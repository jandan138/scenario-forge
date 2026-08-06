from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path

import pytest

from scenario_forge.adapters.labutopia import (
    LabUtopiaInteractiveSceneHandoffError,
    load_labutopia_interactive_scene_handoff,
)


def _digest(path: Path) -> str:
    return "sha256:" + sha256(path.read_bytes()).hexdigest()


def write_interactive_handoff(
    root: Path,
    *,
    scenario_id: str = "task",
    schema_version: str = "labutopia.interactive_scene_handoff/v0.2",
    variant_id: str | None = None,
) -> tuple[Path, Path]:
    package = root / "package"
    translation_x = (
        -1.0199846981
        if variant_id == "source_workbench"
        else -0.436631421014276
        if variant_id == "ebench_workbench"
        else 0.0
    )
    package.mkdir(parents=True)
    for name in ("native.usda", "genmanip.usdc", "vr.usdc"):
        (package / name).write_text(f"#usda 1.0\n# {name}\n", encoding="utf-8")
    source = package / "deps/source/source.usda"
    overlay = package / "deps/source/disable_cube.usda"
    source.parent.mkdir(parents=True)
    source.write_text("#usda 1.0\n", encoding="utf-8")
    overlay.write_text("#usda 1.0\n", encoding="utf-8")
    evidence = package / "evidence/runtime_qualification.json"
    evidence.parent.mkdir()
    evidence.write_text("{}\n", encoding="utf-8")
    if variant_id == "ebench_workbench":
        support_asset = package / "deps/ebench_table/asset.usd"
        support_manifest = package / "deps/ebench_table/evidence/manifest.json"
        support_manifest.parent.mkdir(parents=True)
        support_asset.write_text("#usda 1.0\n", encoding="utf-8")
        support_manifest.write_text(
            json.dumps(
                {
                    "overall_status": "pass",
                    "asset_profile": {
                        "profile_id": "labutopia.lab001.table.static_support"
                    },
                }
            ),
            encoding="utf-8",
        )
    files = []
    for path in sorted(item for item in package.rglob("*") if item.is_file()):
        files.append(
            {
                "path": path.relative_to(package).as_posix(),
                "sha256": _digest(path),
                "size_bytes": path.stat().st_size,
            }
        )
    entrypoints = {}
    for name, rate in (("native", 600), ("genmanip", 600), ("vr", 60)):
        scenario_prim = "/World/_scene" if name == "genmanip" else f"/World/{scenario_id}"
        object_prims = {
            "source_container": f"{scenario_prim}/obj_beaker2",
            "target_container": f"{scenario_prim}/obj_beaker1",
            "support_table": f"{scenario_prim}/obj_table",
        }
        embedded_object_states = {
            "source_container": {
                "prim_path": object_prims["source_container"],
                "position_xyz_m": [0.295 + translation_x, 0.075, 0.8233382266115852],
                "orientation_wxyz": [0.6532814824, 0.6532814824, 0.2705980501, 0.2705980501],
                "local_scale_xyz": [1.0, 1.0, 1.0],
                "world_aabb_m": {
                    "min": [0.2564758473 + translation_x, 0.0364758581, 0.7799941122],
                    "max": [0.3671289439 + translation_x, 0.1471289547, 0.8703945490],
                },
            },
            "target_container": {
                "prim_path": object_prims["target_container"],
                "position_xyz_m": [0.255 + translation_x, -0.245, 0.8406758673476564],
                "orientation_wxyz": [0.6532814824, 0.6532814824, 0.2705980501, 0.2705980501],
                "local_scale_xyz": [1.0, 1.0, 1.0],
                "world_aabb_m": {
                    "min": [0.2010661907 + translation_x, -0.2989337942, 0.7799941122],
                    "max": [0.3559805131 + translation_x, -0.1440194718, 0.9065547133],
                },
            },
            "support_table": {
                "prim_path": object_prims["support_table"],
                "position_xyz_m": [0.2427880660, 0.0, 0.0],
                "orientation_wxyz": [0.0, -1.0, 0.0, 0.0],
                "local_scale_xyz": [0.006, 0.005, 0.004000000059604645],
                "world_aabb_m": (
                    {
                        "min": [-0.3405652207, -0.9325535202, -0.3997177124],
                        "max": [0.8319064971, 0.9187435913, 0.7727605591],
                    }
                    if variant_id == "ebench_workbench"
                    else {
                        "min": [-0.9239185074, -1.3322193410, -0.3997177640],
                        "max": [1.4210249282, 1.3124908584, 0.7727606155],
                    }
                ),
            },
        }
        entrypoints[name] = {
            "path": f"{name}.usd{'a' if name == 'native' else 'c'}",
            "sha256": _digest(package / f"{name}.usd{'a' if name == 'native' else 'c'}"),
            "root_prim": "/World",
            "physics_hz": rate,
            "status": "qualified",
            "hidden_cube_overlay_applied": True,
            "physics_scene_prim": "/World/PhysicsScene" if name == "native" else "/physicsScene",
            "object_prims": object_prims,
            "embedded_object_states": embedded_object_states,
            "particle_prims": {"particles": "/World/task/Particles"},
            "scenario_prim": scenario_prim,
        }
    package_id = (
        f"lab001_pbd_beaker_to_beaker_{variant_id}_v3"
        if variant_id
        else "lab001_pbd_beaker_to_beaker_step600_v2"
    )
    manifest = {
        "schema_version": schema_version,
        "package_id": package_id,
        "producer": "LabUtopia",
        "producer_revision": "producer-r1",
        "source_revision": "source-r1",
        "source": {"path": "deps/source/source.usda", "sha256": _digest(source)},
        "required_overlay": {
            "path": "deps/source/disable_cube.usda",
            "sha256": _digest(overlay),
            "effect": "disable_collision_on_/World/Cube",
        },
        "particle_system": {"kind": "PhysX_PBD", "expected_particle_count": 3600},
        "entrypoints": entrypoints,
        "closure": {"files": files},
        "license": {"identifier": "CC-BY-NC-4.0", "redistributable": False},
        "claims": {
            "contact_grasp_success": False,
            "robot_policy_success": False,
            "liquid_transfer_success": False,
            "benchmark_success": False,
        },
        "runtime_qualification": {
            "status": "qualified",
            "receipts": {"isaac41": "evidence/runtime_qualification.json"},
        },
    }
    if variant_id:
        robot_x = -1.603353277085724 if variant_id == "source_workbench" else -1.02
        support_table: dict[str, object] = {"mode": "embedded_source"}
        if variant_id == "ebench_workbench":
            support_asset = package / "deps/ebench_table/asset.usd"
            support_manifest = package / "deps/ebench_table/evidence/manifest.json"
            support_table = {
                "mode": "external_static_support",
                "asset_entry_prim": "/World/table",
                "required_profile_id": "labutopia.lab001.table.static_support",
                "package": {
                    "path": "deps/ebench_table",
                    "asset_path": "deps/ebench_table/asset.usd",
                    "asset_sha256": _digest(support_asset),
                    "manifest_path": "deps/ebench_table/evidence/manifest.json",
                    "manifest_sha256": _digest(support_manifest),
                    "profile_id": "labutopia.lab001.table.static_support",
                },
            }
        manifest["layout"] = {
            "variant_id": variant_id,
            "task_group_translation_xyz_m": [translation_x, 0.0, 0.0],
            "translated_members": {
                role: {"translation_xyz_m": [translation_x, 0.0, 0.0]}
                for role in ("source_container", "target_container", "particles")
            },
            "tabletop_placement": {
                "hard_edge_clearance_m": 0.1,
                "nominal_edge_clearance_m": 0.105,
                "robot_facing_edge": "x_min",
            },
            "robot_workspace": {
                "profile_ref": "manip/lift2/R5a_isaac41_vr600_v1",
                "spawn_xyz_m": [robot_x, 0.0, 0.31],
                "orientation_wxyz": [1.0, 0.0, 0.0, 0.0],
                "base_footprint_radius_m": 0.35,
                "minimum_table_clearance_m": 0.05,
            },
            "support_table": support_table,
        }
    manifest_path = package / "manifest.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    return package, manifest_path


@pytest.mark.parametrize("variant_id", ["source_workbench", "ebench_workbench"])
def test_loader_accepts_v03_workbench_layout_contract(
    tmp_path: Path, variant_id: str
) -> None:
    package, manifest = write_interactive_handoff(
        tmp_path,
        schema_version="labutopia.interactive_scene_handoff/v0.3",
        variant_id=variant_id,
    )

    handoff = load_labutopia_interactive_scene_handoff(
        package,
        manifest,
        producer_revision="producer-r1",
        expected_package_id=f"lab001_pbd_beaker_to_beaker_{variant_id}_v3",
    )

    assert handoff.manifest["layout"]["variant_id"] == variant_id


@pytest.mark.parametrize("mutation", ["member_translation", "support_hash"])
def test_loader_rejects_invalid_v03_layout_contract(
    tmp_path: Path, mutation: str
) -> None:
    package, manifest_path = write_interactive_handoff(
        tmp_path,
        schema_version="labutopia.interactive_scene_handoff/v0.3",
        variant_id="ebench_workbench",
    )
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if mutation == "member_translation":
        manifest["layout"]["translated_members"]["particles"][
            "translation_xyz_m"
        ][0] += 0.01
    else:
        manifest["layout"]["support_table"]["package"]["asset_sha256"] = (
            "sha256:" + "0" * 64
        )
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    with pytest.raises(LabUtopiaInteractiveSceneHandoffError):
        load_labutopia_interactive_scene_handoff(
            package,
            manifest_path,
            producer_revision="producer-r1",
            expected_package_id="lab001_pbd_beaker_to_beaker_ebench_workbench_v3",
        )


def test_loader_accepts_hash_bound_qualified_three_endpoint_handoff(tmp_path: Path) -> None:
    package, manifest = write_interactive_handoff(tmp_path)

    handoff = load_labutopia_interactive_scene_handoff(
        package,
        manifest,
        producer_revision="producer-r1",
        expected_package_id="lab001_pbd_beaker_to_beaker_step600_v2",
        expected_entrypoints=("native", "genmanip", "vr"),
    )

    source = handoff.to_local_usd_asset_source(
        asset_id="lab001_pbd_scene", attribution=("LabUtopia",)
    )
    assert source.source_usd == package / "native.usda"
    assert source.role == "interactive_composed_scene"
    assert source.redistributable is False
    assert source.upstream_package is not None
    assert source.upstream_package.metadata["entrypoints"]["genmanip"]["physics_hz"] == 600


@pytest.mark.parametrize(
    "mutation", ["tamper", "blocked", "rate", "overlay", "embedded_state"]
)
def test_loader_rejects_unqualified_or_mutated_handoff(tmp_path: Path, mutation: str) -> None:
    package, manifest_path = write_interactive_handoff(tmp_path)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if mutation == "tamper":
        (package / "genmanip.usdc").write_text("tampered", encoding="utf-8")
    elif mutation == "blocked":
        manifest["entrypoints"]["vr"]["status"] = "blocked"
    elif mutation == "rate":
        manifest["entrypoints"]["genmanip"]["physics_hz"] = 60
    elif mutation == "overlay":
        manifest["entrypoints"]["native"]["hidden_cube_overlay_applied"] = False
    else:
        del manifest["entrypoints"]["genmanip"]["embedded_object_states"][
            "support_table"
        ]
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    with pytest.raises(LabUtopiaInteractiveSceneHandoffError):
        load_labutopia_interactive_scene_handoff(
            package,
            manifest_path,
            producer_revision="producer-r1",
            expected_package_id="lab001_pbd_beaker_to_beaker_step600_v2",
            expected_entrypoints=("native", "genmanip", "vr"),
        )

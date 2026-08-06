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
    root: Path, *, scenario_id: str = "task"
) -> tuple[Path, Path]:
    package = root / "package"
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
        entrypoints[name] = {
            "path": f"{name}.usd{'a' if name == 'native' else 'c'}",
            "sha256": _digest(package / f"{name}.usd{'a' if name == 'native' else 'c'}"),
            "root_prim": "/World",
            "physics_hz": rate,
            "status": "qualified",
            "hidden_cube_overlay_applied": True,
            "physics_scene_prim": "/World/PhysicsScene" if name == "native" else "/physicsScene",
            "object_prims": object_prims,
            "particle_prims": {"particles": "/World/task/Particles"},
            "scenario_prim": scenario_prim,
        }
    manifest = {
        "schema_version": "labutopia.interactive_scene_handoff/v0.1",
        "package_id": "lab001_pbd_beaker_to_beaker_step600_v1",
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
    manifest_path = package / "manifest.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    return package, manifest_path


def test_loader_accepts_hash_bound_qualified_three_endpoint_handoff(tmp_path: Path) -> None:
    package, manifest = write_interactive_handoff(tmp_path)

    handoff = load_labutopia_interactive_scene_handoff(
        package,
        manifest,
        producer_revision="producer-r1",
        expected_package_id="lab001_pbd_beaker_to_beaker_step600_v1",
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


@pytest.mark.parametrize("mutation", ["tamper", "blocked", "rate", "overlay"])
def test_loader_rejects_unqualified_or_mutated_handoff(tmp_path: Path, mutation: str) -> None:
    package, manifest_path = write_interactive_handoff(tmp_path)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if mutation == "tamper":
        (package / "genmanip.usdc").write_text("tampered", encoding="utf-8")
    elif mutation == "blocked":
        manifest["entrypoints"]["vr"]["status"] = "blocked"
    elif mutation == "rate":
        manifest["entrypoints"]["genmanip"]["physics_hz"] = 60
    else:
        manifest["entrypoints"]["native"]["hidden_cube_overlay_applied"] = False
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    with pytest.raises(LabUtopiaInteractiveSceneHandoffError):
        load_labutopia_interactive_scene_handoff(
            package,
            manifest_path,
            producer_revision="producer-r1",
            expected_package_id="lab001_pbd_beaker_to_beaker_step600_v1",
            expected_entrypoints=("native", "genmanip", "vr"),
        )

from __future__ import annotations

import json
from pathlib import Path

from pxr import Usd, UsdGeom, UsdPhysics
import yaml

from scenario_forge.generation.source_resolver import (
    resolve_scenario_source_bindings,
)


ROOT = Path(__file__).resolve().parents[1]
BINDINGS = (
    ROOT
    / "configs/source_bindings/"
    "scientific_workbench_tube15_long_neck_threaded_v1_20260901.yaml"
)
READINESS = (
    ROOT
    / "configs/asset_readiness/"
    "scientific_workbench_tube15_long_neck_threaded_v1_20260901.yaml"
)
PRODUCER = Path(
    "/cpfs/user/zhuzihou/dev/ConvertAsset/outputs/"
    "tube15_long_neck_threaded_geometry_v1_20260901"
)


def test_long_neck_threaded_assets_resolve_as_separate_rigid_packages() -> None:
    sources = resolve_scenario_source_bindings(BINDINGS)
    assert set(sources) == {
        "scientific_workbench_tube15_long_neck_threaded_body_v1",
        "scientific_workbench_tube15_long_neck_threaded_closed_cap_v1",
    }
    for source in sources.values():
        assert source.role == "rigid_object"
        assert source.source_usd.is_file()


def test_long_neck_threaded_packages_keep_identity_dynamic_sdf_entries() -> None:
    payload = yaml.safe_load(BINDINGS.read_text(encoding="utf-8"))
    for binding in payload["bindings"].values():
        package = Path(binding["source_usd"]).parent
        manifest = json.loads(
            (package / "evidence/manifest.json").read_text(encoding="utf-8")
        )
        assert manifest["overall_status"] == "pass"
        assert manifest["claims"]["dynamic_geometry_ready"] is True
        assert manifest["claims"]["sdf_collision_ready"] is True
        assert manifest["claims"]["thread_interaction_ready"] is False
        stage = Usd.Stage.Open(str(package / "asset.usd"))
        root = stage.GetPrimAtPath(binding["root_prim_path"])
        assert root and root.HasAPI(UsdPhysics.RigidBodyAPI)
        assert root.HasAPI(UsdPhysics.MassAPI)
        assert UsdGeom.Xformable(root).GetOrderedXformOps() == []
        colliders = [
            prim
            for prim in stage.Traverse()
            if prim.HasAPI(UsdPhysics.CollisionAPI)
        ]
        assert len(colliders) == 1
        assert colliders[0].GetAttribute("physics:approximation").Get() == "sdf"


def test_readiness_promotes_geometry_but_blocks_thread_task_and_liquid() -> None:
    readiness = yaml.safe_load(READINESS.read_text(encoding="utf-8"))
    assert readiness["asset_set_id"] == "tube15_long_neck_threaded_v1"
    assert readiness["producer_manifest"].endswith("/asset_set_manifest.json")
    assert readiness["readiness"] == {
        "geometry": "ready",
        "dynamic_runtime": "ready",
        "sdf_collision": "ready",
        "thread_interaction": "blocked",
        "task08": "blocked",
        "liquid_container": "not_requested",
    }
    assert readiness["consumer_policy"]["allow_separate_asset_placement"] is True
    assert readiness["consumer_policy"]["allow_thread_task_claim"] is False
    assert readiness["consumer_policy"]["allow_physics_override"] is False
    assert PRODUCER.is_dir()

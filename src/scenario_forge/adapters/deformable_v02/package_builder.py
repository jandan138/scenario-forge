"""Builder for M2 v0.2 dual-engine deformable scenario packages."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from scenario_forge.adapters.deformable_v02.usd_localizer import (
    create_cloth_caddy_tray_usd,
    create_pastry_box_hinged_usd,
    create_robot_pedestal_usd,
    create_serving_plate_usd,
    create_wipe_zone_mat_usd,
    localize_deformable_asset_from_m1,
    localize_usd_asset_closures,
    vendor_franka_panda_assets,
)
from scenario_forge.assets.checksum import compute_sha256
from scenario_forge.assets.lock import generate_asset_lock, write_asset_lock


@dataclass(frozen=True)
class PilotAssetSpec:
    asset_id: str
    role: str
    asset_type: str
    license: str
    source_kind: str
    source_uri: str


@dataclass(frozen=True)
class DeformablePilotPackageResult:
    package_id: str
    package_root: Path
    scene_usd: Path
    asset_count: int
    deformable_asset_id: str
    structural_family: str


PILOT_TASK_SPECS: dict[str, dict[str, Any]] = {
    "coffee_bar_fragile_pastry_plate": {
        "source_package": "specialty_coffee_bar_creatista_prep",
        "domain": "specialty_coffee_bar",
        "task_family": "articulated_open_and_fragile_deformable_pick_place",
        "instruction": (
            "打开桌面上带有铰链上盖的点心展示盒，采用触觉力控柔顺夹持"
            "完整取出易碎奶油千层糕点，旋转手腕平稳抬升并轻放至瓷质甜点盘中央，"
            "全程保持材料内部变形损伤低于阈值。"
        ),
        "room_asset_id": "out_of_domain_env_kitchen_coffee_bar_v2",
        "copied_prop_assets": (
            "standard_table",
            "NespressoCreatistaPlus",
            "EspressoCup",
            "CoffeeCapsule",
            "MilkPitcher",
        ),
        "m1_asset_id": "pilot_fragile_chocopie_tofu_01",
        "deformable_instance_id": "fragile_pastry",
        "deformable_prim_name": "fragile_pastry",
        "deformable_pose": {"xyz": [-0.18, -0.02, 0.766], "wxyz": [1.0, 0.0, 0.0, 0.0]},
    },
    "office_desk_wiping_cloth_clean_and_park": {
        "source_package": "modern_office_brother_calibrate",
        "domain": "modern_office",
        "task_family": "deformable_cloth_wiping_and_parking",
        "instruction": (
            "在现代办公桌面上柔顺抓起微纤维擦拭布，"
            "按力矩受控下压力依次擦拭三个目标点位并保持布面无撕裂过拉伸，"
            "随后抬起并轻放收纳至桦木收纳托盘内。"
        ),
        "room_asset_id": "out_of_domain_env_office_print_studio_v2",
        "copied_prop_assets": (
            "standard_table",
            "BrotherMFCL2820DW",
            "A5MediaPack",
            "CalibrationSheet",
            "OfficePenOrganizer",
        ),
        "m1_asset_id": "pilot_flexible_wiping_cloth_01",
        "deformable_instance_id": "wiping_cloth",
        "deformable_prim_name": "wiping_cloth",
        "deformable_pose": {"xyz": [-0.13, -0.02, 0.758], "wxyz": [1.0, 0.0, 0.0, 0.0]},
    },
}


def _write_yaml(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True), encoding="utf-8")


def _default_repo_roots() -> tuple[Path, Path]:
    repo_root = Path(__file__).resolve().parents[4]
    source_packages_root = (
        repo_root
        / "external_artifacts"
        / "out_of_domain_factory_r3_20261113"
        / "packages"
    )
    return repo_root, source_packages_root


def _asset_entry(package_root: Path, spec: PilotAssetSpec, canonical_rel: str) -> dict[str, Any]:
    asset_file = package_root / canonical_rel
    return {
        "asset_id": spec.asset_id,
        "role": spec.role,
        "asset_type": spec.asset_type,
        "canonical_usd": canonical_rel,
        "license": spec.license,
        "sha256": compute_sha256(asset_file),
        "source_kind": spec.source_kind,
        "source_uri": spec.source_uri,
        "resolver_version": "scenario-forge/deformable-v0.2-localizer",
    }


def _build_coffee_bar_package(
    pkg_root: Path,
    source_assets_root: Path,
    m1_dir: Path,
) -> DeformablePilotPackageResult:
    task_id = "coffee_bar_fragile_pastry_plate"
    assets_root = pkg_root / "assets"
    copied_ids = (
        "out_of_domain_env_kitchen_coffee_bar_v2",
        "standard_table",
        "NespressoCreatistaPlus",
        "EspressoCup",
        "CoffeeCapsule",
        "MilkPitcher",
    )
    broken = localize_usd_asset_closures(source_assets_root, assets_root, copied_ids)
    if broken:
        raise ValueError(f"Broken USD links found during localization: {broken}")

    vendor_franka_panda_assets(assets_root / "franka_panda")
    create_robot_pedestal_usd(assets_root / "robot_pedestal")
    create_pastry_box_hinged_usd(assets_root / "pastry_box_hinged")
    create_serving_plate_usd(assets_root / "serving_plate")
    deformable_info = localize_deformable_asset_from_m1(
        m1_dir,
        assets_root / "pilot_fragile_chocopie_tofu_01",
        prim_name="fragile_pastry",
    )

    m1_manifest = deformable_info["m1_manifest"]
    source_meta = m1_manifest["source"]
    budget = m1_manifest["integrity_budget"]
    all_parity_ok = all(bool(v.get("parity_verified", False)) for v in m1_manifest.get("engines", {}).values())

    scene_usda = """#usda 1.0
(
    defaultPrim = "World"
    metersPerUnit = 1
    upAxis = "Z"
    subLayers = [
        @../assets/pilot_fragile_chocopie_tofu_01/asset.usd@,
        @../assets/pastry_box_hinged/asset.usd@,
        @../assets/serving_plate/asset.usd@,
        @../assets/franka_panda/asset.usd@,
        @../assets/robot_pedestal/asset.usd@,
        @../assets/standard_table/asset.usd@,
        @../assets/NespressoCreatistaPlus/asset.usd@,
        @../assets/EspressoCup/asset.usd@,
        @../assets/CoffeeCapsule/asset.usd@,
        @../assets/out_of_domain_env_kitchen_coffee_bar_v2/asset.usd@,
    ]
)

over "World"
{
    double3 xformOp:translate = (0, 0, 0)
    quatd xformOp:orient = (1, 0, 0, 0)
    uniform token[] xformOpOrder = ["xformOp:translate", "xformOp:orient"]

    over "table"
    {
        double3 xformOp:translate = (0, 0, 0)
        quatd xformOp:orient = (1, 0, 0, 0)
        uniform token[] xformOpOrder = ["!resetXformStack!", "xformOp:translate", "xformOp:orient"]
    }

    over "robot_pedestal"
    {
        double3 xformOp:translate = (0, -0.48, 0)
        quatd xformOp:orient = (1, 0, 0, 0)
        uniform token[] xformOpOrder = ["!resetXformStack!", "xformOp:translate", "xformOp:orient"]
    }

    over "franka_panda"
    {
        double3 xformOp:translate = (0, -0.48, 0.755)
        quatd xformOp:orient = (0.7071067812, 0, 0, 0.7071067812)
        uniform token[] xformOpOrder = ["!resetXformStack!", "xformOp:translate", "xformOp:orient"]
    }

    over "pastry_box_hinged"
    {
        double3 xformOp:translate = (-0.18, -0.02, 0.755)
        quatd xformOp:orient = (1, 0, 0, 0)
        uniform token[] xformOpOrder = ["!resetXformStack!", "xformOp:translate", "xformOp:orient"]
    }

    over "fragile_pastry"
    {
        double3 xformOp:translate = (-0.18, -0.02, 0.766)
        quatd xformOp:orient = (1, 0, 0, 0)
        uniform token[] xformOpOrder = ["!resetXformStack!", "xformOp:translate", "xformOp:orient"]
    }

    over "serving_plate"
    {
        double3 xformOp:translate = (0.18, -0.02, 0.755)
        quatd xformOp:orient = (1, 0, 0, 0)
        uniform token[] xformOpOrder = ["!resetXformStack!", "xformOp:translate", "xformOp:orient"]
    }

    over "NespressoCreatistaPlus"
    {
        double3 xformOp:translate = (-0.56, 0.15, 0.755)
        quatd xformOp:orient = (1, 0, 0, 0)
        uniform token[] xformOpOrder = ["!resetXformStack!", "xformOp:translate", "xformOp:orient"]
    }

    over "EspressoCup"
    {
        double3 xformOp:translate = (-0.36, 0.22, 0.757)
        quatd xformOp:orient = (1, 0, 0, 0)
        uniform token[] xformOpOrder = ["!resetXformStack!", "xformOp:translate", "xformOp:orient"]
    }

    over "CoffeeCapsule"
    {
        double3 xformOp:translate = (-0.46, -0.06, 0.757)
        quatd xformOp:orient = (1, 0, 0, 0)
        uniform token[] xformOpOrder = ["!resetXformStack!", "xformOp:translate", "xformOp:orient"]
    }

    def Xform "milk_pitcher" (
        prepend references = @../assets/MilkPitcher/asset.usd@</root>
    )
    {
        double3 xformOp:translate = (0.52, 0.16, 0.757)
        quatd xformOp:orient = (1, 0, 0, 0)
        double3 xformOp:scale = (1, 1, 1)
        uniform token[] xformOpOrder = ["!resetXformStack!", "xformOp:translate", "xformOp:orient", "xformOp:scale"]
    }
}
"""
    scene_path = pkg_root / "scene" / "main.usda"
    scene_path.parent.mkdir(parents=True, exist_ok=True)
    scene_path.write_text(scene_usda, encoding="utf-8")

    asset_specs = [
        PilotAssetSpec("out_of_domain_env_kitchen_coffee_bar_v2", "environment", "usd_scene", "LicenseRef-Internal-Generated", "external_usd_package", "scenario-forge://specialty_coffee_bar_creatista_prep/assets/out_of_domain_env_kitchen_coffee_bar_v2"),
        PilotAssetSpec("standard_table", "support_surface", "usd_component", "LicenseRef-Internal-LabUtopia-Derived", "external_usd_package", "scenario-forge://specialty_coffee_bar_creatista_prep/assets/standard_table"),
        PilotAssetSpec("NespressoCreatistaPlus", "context_prop", "usd_component", "LicenseRef-Team-Owned-Procedural", "external_usd_package", "scenario-forge://specialty_coffee_bar_creatista_prep/assets/NespressoCreatistaPlus"),
        PilotAssetSpec("EspressoCup", "context_prop", "usd_component", "LicenseRef-Team-Owned-Procedural", "external_usd_package", "scenario-forge://specialty_coffee_bar_creatista_prep/assets/EspressoCup"),
        PilotAssetSpec("CoffeeCapsule", "context_prop", "usd_component", "LicenseRef-Team-Owned-Procedural", "external_usd_package", "scenario-forge://specialty_coffee_bar_creatista_prep/assets/CoffeeCapsule"),
        PilotAssetSpec("MilkPitcher", "context_prop", "usd_component", "LicenseRef-Team-Owned-Procedural", "external_usd_package", "scenario-forge://specialty_coffee_bar_creatista_prep/assets/MilkPitcher"),
        PilotAssetSpec("robot_pedestal", "support_fixture", "usd_component", "LicenseRef-Team-Owned-Procedural", "generated_procedural_usd", "scenario-forge://deformable_v02/robot_pedestal"),
        PilotAssetSpec("franka_panda", "robot_embodiment", "usd_articulation", "Apache-2.0", "vendored_local_urdf_usd", "scenario-forge://deformable_v02/franka_panda"),
        PilotAssetSpec("pastry_box_hinged", "articulated_container", "usd_articulation", "LicenseRef-Team-Owned-Procedural", "generated_procedural_usd", "scenario-forge://deformable_v02/pastry_box_hinged"),
        PilotAssetSpec("serving_plate", "target_container", "usd_component", "LicenseRef-Team-Owned-Procedural", "generated_procedural_usd", "scenario-forge://deformable_v02/serving_plate"),
        PilotAssetSpec("pilot_fragile_chocopie_tofu_01", "deformable_manipulated_object", "usd_deformable_tetmesh", "LicenseRef-Team-Owned-Procedural", "convert_asset_m1_bundle", "convert-asset://deformable_pilot_m1/pilot_fragile_chocopie_tofu_01"),
    ]

    _write_yaml(
        pkg_root / "assets" / "asset_manifest.yaml",
        {
            "schema_version": "asset-manifest/v0.2",
            "assets": [_asset_entry(pkg_root, s, f"assets/{s.asset_id}/asset.usd") for s in asset_specs],
        },
    )

    instances_data = {
        "schema_version": "scene-instances/v0.2",
        "coordinate_system": {"units": "meters", "up_axis": "Z"},
        "instances": [
            {"id": "table", "asset_id": "standard_table", "source_prim_path": "/World/table", "role": "table", "pose": {"xyz": [0.0, 0.0, 0.0], "wxyz": [1.0, 0.0, 0.0, 0.0]}, "semantic_tags": ["table"], "initial_state": {}},
            {"id": "robot_pedestal", "asset_id": "robot_pedestal", "source_prim_path": "/World/robot_pedestal", "role": "support_fixture", "pose": {"xyz": [0.0, -0.48, 0.0], "wxyz": [1.0, 0.0, 0.0, 0.0]}, "semantic_tags": ["pedestal"], "initial_state": {}},
            {"id": "pastry_box_hinged", "asset_id": "pastry_box_hinged", "source_prim_path": "/World/pastry_box_hinged", "role": "articulated_container", "pose": {"xyz": [-0.18, -0.02, 0.755], "wxyz": [1.0, 0.0, 0.0, 0.0]}, "named_frames": {"lid_tab": {"xyz": [0.0, -0.066, 0.048], "wxyz": [1.0, 0.0, 0.0, 0.0]}, "interior_center": {"xyz": [0.0, 0.0, 0.011], "wxyz": [1.0, 0.0, 0.0, 0.0]}}, "semantic_tags": ["articulated_container"], "initial_state": {"lid_hinge": 0.0}},
            {
                "id": "fragile_pastry",
                "asset_id": "pilot_fragile_chocopie_tofu_01",
                "source_prim_path": "/World/fragile_pastry",
                "role": "deformable_manipulated_object",
                "pose": {"xyz": [-0.18, -0.02, 0.766], "wxyz": [1.0, 0.0, 0.0, 0.0]},
                "semantic_tags": ["deformable", "fragile_pastry", "soft_solid"],
                "initial_state": {"deformable_family": "soft_solid"},
                "deformable": {
                    "asset_id": "pilot_fragile_chocopie_tofu_01",
                    "structural_family": "soft_solid",
                    "youngs_modulus_pa": float(source_meta.get("youngs_modulus_pa", 28000.0)),
                    "poissons_ratio": float(source_meta.get("poissons_ratio", 0.32)),
                    "strain_metric": str(budget.get("strain_metric", "polar_stretch_frobenius_q95")),
                    "strain_onset_a": float(budget.get("strain_onset_a", 0.15)),
                    "strain_failure_b": float(budget.get("strain_failure_b", 0.45)),
                    "damage_threshold": float(budget.get("damage_threshold", 0.25)),
                    "max_normal_force_n": float(budget.get("max_normal_force_n", 68.1113)),
                    "mass_kg": float(source_meta.get("mass_kg", 0.13034)),
                    "dimensions_m": [0.07, 0.07, 0.028],
                    "engine_configs": {
                        "genesis": "assets/pilot_fragile_chocopie_tofu_01/engines/genesis/genesis_config.json",
                        "mujoco4": "assets/pilot_fragile_chocopie_tofu_01/engines/mujoco4/mujoco4_asset.json",
                        "newton18": "assets/pilot_fragile_chocopie_tofu_01/engines/newton18/newton_config.json",
                        "isaac_physx": "assets/pilot_fragile_chocopie_tofu_01/engines/isaac_physx/isaac_physx_config.json",
                    },
                },
            },
            {"id": "serving_plate", "asset_id": "serving_plate", "source_prim_path": "/World/serving_plate", "role": "target_container", "pose": {"xyz": [0.18, -0.02, 0.755], "wxyz": [1.0, 0.0, 0.0, 0.0]}, "named_frames": {"plate_center": {"xyz": [0.0, 0.0, 0.008], "wxyz": [1.0, 0.0, 0.0, 0.0]}}, "semantic_tags": ["serving_plate"], "initial_state": {}},
            {"id": "creatista_machine", "asset_id": "NespressoCreatistaPlus", "source_prim_path": "/World/NespressoCreatistaPlus", "role": "context_prop", "pose": {"xyz": [-0.56, 0.15, 0.755], "wxyz": [1.0, 0.0, 0.0, 0.0]}, "semantic_tags": ["context_prop"], "initial_state": {}},
            {"id": "espresso_cup", "asset_id": "EspressoCup", "source_prim_path": "/World/EspressoCup", "role": "context_prop", "pose": {"xyz": [-0.36, 0.22, 0.757], "wxyz": [1.0, 0.0, 0.0, 0.0]}, "semantic_tags": ["context_prop"], "initial_state": {}},
            {"id": "coffee_capsule", "asset_id": "CoffeeCapsule", "source_prim_path": "/World/CoffeeCapsule", "role": "context_prop", "pose": {"xyz": [-0.46, -0.06, 0.757], "wxyz": [1.0, 0.0, 0.0, 0.0]}, "semantic_tags": ["context_prop"], "initial_state": {}},
            {"id": "milk_pitcher", "asset_id": "MilkPitcher", "source_prim_path": "/root", "role": "context_prop", "pose": {"xyz": [0.52, 0.16, 0.757], "wxyz": [1.0, 0.0, 0.0, 0.0]}, "semantic_tags": ["context_prop"], "initial_state": {}},
        ],
    }
    _write_yaml(pkg_root / "scene" / "instances.yaml", instances_data)

    _write_yaml(
        pkg_root / "robot" / "robot.yaml",
        {
            "schema_version": "robot/v0.2",
            "profile_ref": "manip/franka_panda/tabletop_9dof_v1",
            "urdf_path": "assets/franka_panda/panda.urdf",
            "mjcf_path": "assets/franka_panda/panda.xml",
            "usd_path": "assets/franka_panda/asset.usd",
            "action_dim": 9,
            "spawn": {"xyz": [0.0, -0.48, 0.755], "wxyz": [0.7071067812, 0.0, 0.0, 0.7071067812]},
            "actors": [{"id": "panda_arm", "end_effector": "panda_grasptarget", "capabilities": ["open_hinge", "tactile_grasp", "lift_rotate", "place", "release"]}],
        },
    )

    _write_yaml(
        pkg_root / "task" / "task.yaml",
        {
            "schema_version": "task/v0.5",
            "task_id": task_id,
            "task_family": "articulated_open_and_fragile_deformable_pick_place",
            "instruction": PILOT_TASK_SPECS[task_id]["instruction"],
            "bindings": {
                "objects": {
                    "table": "table",
                    "articulated_container": "pastry_box_hinged",
                    "manipulated_deformable": "fragile_pastry",
                    "target_container": "serving_plate",
                },
                "actors": {"arm": "panda_arm"},
            },
            "steps": [
                {"id": "open_pastry_box_lid", "skill": "open_articulated_part", "actors": ["panda_arm"], "parameters": {"object": "pastry_box_hinged", "joint": "lid_hinge", "target_state": "open_wide"}},
                {"id": "grasp_fragile_pastry", "skill": "tactile_grasp", "actors": ["panda_arm"], "parameters": {"object": "fragile_pastry", "max_normal_force_n": 18.0}, "depends_on": ["open_pastry_box_lid"]},
                {"id": "lift_and_rotate_pastry", "skill": "lift_rotate", "actors": ["panda_arm"], "parameters": {"object": "fragile_pastry", "wrist_yaw_deg": 35.0}, "depends_on": ["grasp_fragile_pastry"]},
                {"id": "place_on_serving_plate", "skill": "place", "actors": ["panda_arm"], "parameters": {"object": "fragile_pastry", "target": "serving_plate", "target_frame": "serving_plate.plate_center"}, "depends_on": ["lift_and_rotate_pastry"]},
            ],
        },
    )
    _write_yaml(
        pkg_root / "task" / "graph.yaml",
        {
            "schema_version": "task-graph/v0.2",
            "nodes": [
                {"id": "open_pastry_box_lid", "skill": "open_articulated_part", "actors": ["panda_arm"]},
                {"id": "grasp_fragile_pastry", "skill": "tactile_grasp", "actors": ["panda_arm"]},
                {"id": "lift_and_rotate_pastry", "skill": "lift_rotate", "actors": ["panda_arm"]},
                {"id": "place_on_serving_plate", "skill": "place", "actors": ["panda_arm"]},
            ],
            "edges": [
                {"from": "open_pastry_box_lid", "to": "grasp_fragile_pastry"},
                {"from": "grasp_fragile_pastry", "to": "lift_and_rotate_pastry"},
                {"from": "lift_and_rotate_pastry", "to": "place_on_serving_plate"},
            ],
        },
    )
    _write_yaml(
        pkg_root / "task" / "predicates.yaml",
        {
            "schema_version": "predicates/v0.2",
            "success_predicates": [
                {"id": "lid_opened", "type": "articulation_joint_state_reached", "sequence_index": 0, "parameters": {"object": "pastry_box_hinged", "joint": "lid_hinge", "min_angle_rad": 1.15}},
                {"id": "pastry_lifted", "type": "deformable_com_height_reached", "sequence_index": 1, "parameters": {"object": "fragile_pastry", "min_z": 0.85}},
                {"id": "pastry_placed_on_plate", "type": "relative_pose_reached", "sequence_index": 2, "parameters": {"object": "fragile_pastry", "relative_to": "serving_plate", "max_xy_err": 0.055}},
                {"id": "pastry_integrity_preserved", "type": "deformable_integrity_preserved", "sequence_index": 3, "parameters": {"object": "fragile_pastry", "max_polar_stretch_q95": 0.20, "max_damage_score": 0.25}},
            ],
        },
    )
    _write_yaml(
        pkg_root / "metrics" / "metrics.yaml",
        {
            "schema_version": "metrics/v0.4",
            "aggregation": {"type": "weighted_progress_score", "normalization": "declared_sum", "inactive_treatment": "zero"},
            "metrics": [
                {"id": "stage0_lid_opened", "type": "rubric_condition", "role": "progress_component", "weight": 0.25, "active": True, "source_ref": {"step_id": "open_pastry_box_lid"}},
                {"id": "stage1_pastry_lifted", "type": "rubric_condition", "role": "progress_component", "weight": 0.25, "active": True, "source_ref": {"step_id": "lift_and_rotate_pastry"}},
                {"id": "stage2_pastry_on_plate", "type": "rubric_condition", "role": "progress_component", "weight": 0.25, "active": True, "source_ref": {"step_id": "place_on_serving_plate"}},
                {"id": "stage3_deformable_intact", "type": "deformable_integrity_gate", "role": "progress_component", "weight": 0.25, "active": True, "parameters": {"strain_onset_a": float(budget.get("strain_onset_a", 0.15)), "strain_failure_b": float(budget.get("strain_failure_b", 0.45)), "damage_threshold": float(budget.get("damage_threshold", 0.25))}},
            ],
        },
    )
    _write_yaml(
        pkg_root / "scenario.yaml",
        {
            "schema_version": "scenario-spec/v0.6",
            "scenario_id": task_id,
            "domain": "specialty_coffee_bar",
            "task_family": "articulated_open_and_fragile_deformable_pick_place",
            "instruction": PILOT_TASK_SPECS[task_id]["instruction"],
            "scene": {"asset_id": "out_of_domain_env_kitchen_coffee_bar_v2", "root_prim_path": "/World", "pose": {"xyz": [0.0, 0.0, 0.0], "wxyz": [1.0, 0.0, 0.0, 0.0]}},
            "objects": instances_data["instances"],
        },
    )
    _write_yaml(
        pkg_root / "generation" / "plan.yaml",
        {
            "schema_version": "scenario-generation-plan/v0.2",
            "package_id": task_id,
            "source_spec": "scenario.yaml",
            "operations": [
                {"type": "localize_room_and_props", "source_package": "specialty_coffee_bar_creatista_prep"},
                {"type": "vendor_franka_panda", "destination": "assets/franka_panda"},
                {"type": "localize_m1_deformable", "asset_id": "pilot_fragile_chocopie_tofu_01"},
                {"type": "compose_usd_scene", "output": "scene/main.usda"},
                {"type": "lock_assets", "output": "locks/asset_lock.yaml"},
            ],
        },
    )
    _write_yaml(
        pkg_root / "evidence" / "validation_report.yaml",
        {
            "schema_version": "validation-report/v0.2",
            "package_id": task_id,
            "status": "passed",
            "overall_level": "asset_locked",
            "checks": [
                {"id": "local_usd_closures_copied", "status": "passed", "asset_count": len(asset_specs)},
                {"id": "m1_deformable_parity_ingested", "status": "passed", "all_parity_verified": all_parity_ok},
                {"id": "asset_lock_generated", "status": "passed"},
            ],
            "runtime_claims": [],
        },
    )
    _write_yaml(
        pkg_root / "provenance" / "provenance.yaml",
        {
            "schema_version": "scenario-provenance/v0.2",
            "package_id": task_id,
            "generator": "scenario-forge",
            "scenario_spec": "scenario.yaml",
            "m1_source_manifest_sha256": compute_sha256(m1_dir / "manifest.json"),
            "assets": [
                {
                    "asset_id": s.asset_id,
                    "source_uri": s.source_uri,
                    "license": s.license,
                    "canonical_usd": f"assets/{s.asset_id}/asset.usd",
                    "sha256": compute_sha256(pkg_root / f"assets/{s.asset_id}/asset.usd"),
                }
                for s in asset_specs
            ],
        },
    )
    _write_yaml(
        pkg_root / "manifest.yaml",
        {
            "schema_version": "scenario-package/v0.2",
            "package_id": task_id,
            "scenario_domain": "specialty_coffee_bar_service",
            "package_mode": "fat",
            "targets": ["ebench", "embodied-eval-os"],
            "entrypoints": {
                "generation_plan": "generation/plan.yaml",
                "scenario_spec": "scenario.yaml",
                "scene_usd": "scene/main.usda",
                "scene_instances": "scene/instances.yaml",
                "task": "task/task.yaml",
                "task_graph": "task/graph.yaml",
                "predicates": "task/predicates.yaml",
                "robot": "robot/robot.yaml",
                "metrics": "metrics/metrics.yaml",
            },
            "assets": {"manifest": "assets/asset_manifest.yaml", "lock": "locks/asset_lock.yaml"},
            "validation": {"report": "evidence/validation_report.yaml", "minimum_required_level": "asset_locked"},
            "provenance": {"summary": "provenance/provenance.yaml"},
        },
    )
    write_asset_lock(pkg_root, generate_asset_lock(pkg_root, lock_id=f"{task_id}_asset_lock"))
    return DeformablePilotPackageResult(
        package_id=task_id,
        package_root=pkg_root,
        scene_usd=scene_path,
        asset_count=len(asset_specs),
        deformable_asset_id="pilot_fragile_chocopie_tofu_01",
        structural_family="soft_solid",
    )


def _build_office_cloth_package(
    pkg_root: Path,
    source_assets_root: Path,
    m1_dir: Path,
) -> DeformablePilotPackageResult:
    task_id = "office_desk_wiping_cloth_clean_and_park"
    assets_root = pkg_root / "assets"
    copied_ids = (
        "out_of_domain_env_office_print_studio_v2",
        "standard_table",
        "BrotherMFCL2820DW",
        "A5MediaPack",
        "CalibrationSheet",
        "OfficePenOrganizer",
    )
    broken = localize_usd_asset_closures(source_assets_root, assets_root, copied_ids)
    if broken:
        raise ValueError(f"Broken USD links found during localization: {broken}")

    vendor_franka_panda_assets(assets_root / "franka_panda")
    create_robot_pedestal_usd(assets_root / "robot_pedestal")
    create_wipe_zone_mat_usd(assets_root / "wipe_zone_mat")
    create_cloth_caddy_tray_usd(assets_root / "cloth_caddy_tray")
    deformable_info = localize_deformable_asset_from_m1(
        m1_dir,
        assets_root / "pilot_flexible_wiping_cloth_01",
        prim_name="wiping_cloth",
    )

    m1_manifest = deformable_info["m1_manifest"]
    source_meta = m1_manifest["source"]
    budget = m1_manifest["integrity_budget"]
    all_parity_ok = all(bool(v.get("parity_verified", False)) for v in m1_manifest.get("engines", {}).values())

    scene_usda = """#usda 1.0
(
    defaultPrim = "World"
    metersPerUnit = 1
    upAxis = "Z"
    subLayers = [
        @../assets/pilot_flexible_wiping_cloth_01/asset.usd@,
        @../assets/wipe_zone_mat/asset.usd@,
        @../assets/cloth_caddy_tray/asset.usd@,
        @../assets/franka_panda/asset.usd@,
        @../assets/robot_pedestal/asset.usd@,
        @../assets/standard_table/asset.usd@,
        @../assets/BrotherMFCL2820DW/asset.usd@,
        @../assets/A5MediaPack/asset.usd@,
        @../assets/CalibrationSheet/asset.usd@,
        @../assets/out_of_domain_env_office_print_studio_v2/asset.usd@,
    ]
)

over "World"
{
    double3 xformOp:translate = (0, 0, 0)
    quatd xformOp:orient = (1, 0, 0, 0)
    uniform token[] xformOpOrder = ["xformOp:translate", "xformOp:orient"]

    over "table"
    {
        double3 xformOp:translate = (0, 0, 0)
        quatd xformOp:orient = (1, 0, 0, 0)
        uniform token[] xformOpOrder = ["!resetXformStack!", "xformOp:translate", "xformOp:orient"]
    }

    over "robot_pedestal"
    {
        double3 xformOp:translate = (0, -0.48, 0)
        quatd xformOp:orient = (1, 0, 0, 0)
        uniform token[] xformOpOrder = ["!resetXformStack!", "xformOp:translate", "xformOp:orient"]
    }

    over "franka_panda"
    {
        double3 xformOp:translate = (0, -0.48, 0.755)
        quatd xformOp:orient = (0.7071067812, 0, 0, 0.7071067812)
        uniform token[] xformOpOrder = ["!resetXformStack!", "xformOp:translate", "xformOp:orient"]
    }

    over "wipe_zone_mat"
    {
        double3 xformOp:translate = (-0.04, 0.02, 0.755)
        quatd xformOp:orient = (1, 0, 0, 0)
        uniform token[] xformOpOrder = ["!resetXformStack!", "xformOp:translate", "xformOp:orient"]
    }

    over "wiping_cloth"
    {
        double3 xformOp:translate = (-0.13, -0.02, 0.758)
        quatd xformOp:orient = (1, 0, 0, 0)
        uniform token[] xformOpOrder = ["!resetXformStack!", "xformOp:translate", "xformOp:orient"]
    }

    over "cloth_caddy_tray"
    {
        double3 xformOp:translate = (0.22, -0.04, 0.755)
        quatd xformOp:orient = (1, 0, 0, 0)
        uniform token[] xformOpOrder = ["!resetXformStack!", "xformOp:translate", "xformOp:orient"]
    }

    over "BrotherMFCL2820DW"
    {
        double3 xformOp:translate = (-0.58, 0.12, 0.755)
        quatd xformOp:orient = (1, 0, 0, 0)
        uniform token[] xformOpOrder = ["!resetXformStack!", "xformOp:translate", "xformOp:orient"]
    }

    over "A5MediaPack"
    {
        double3 xformOp:translate = (-0.44, -0.18, 0.757)
        quatd xformOp:orient = (0.707107, 0, 0, 0.707107)
        uniform token[] xformOpOrder = ["!resetXformStack!", "xformOp:translate", "xformOp:orient"]
    }

    over "CalibrationSheet"
    {
        double3 xformOp:translate = (0.48, -0.14, 0.757)
        quatd xformOp:orient = (0.707107, 0, 0, 0.707107)
        uniform token[] xformOpOrder = ["!resetXformStack!", "xformOp:translate", "xformOp:orient"]
    }

    def Xform "office_pen_organizer" (
        prepend references = @../assets/OfficePenOrganizer/asset.usd@</root>
    )
    {
        double3 xformOp:translate = (0.52, 0.18, 0.757)
        quatd xformOp:orient = (1, 0, 0, 0)
        double3 xformOp:scale = (1, 1, 1)
        uniform token[] xformOpOrder = ["!resetXformStack!", "xformOp:translate", "xformOp:orient", "xformOp:scale"]
    }
}
"""
    scene_path = pkg_root / "scene" / "main.usda"
    scene_path.parent.mkdir(parents=True, exist_ok=True)
    scene_path.write_text(scene_usda, encoding="utf-8")

    asset_specs = [
        PilotAssetSpec("out_of_domain_env_office_print_studio_v2", "environment", "usd_scene", "LicenseRef-Internal-Generated", "external_usd_package", "scenario-forge://modern_office_brother_calibrate/assets/out_of_domain_env_office_print_studio_v2"),
        PilotAssetSpec("standard_table", "support_surface", "usd_component", "LicenseRef-Internal-LabUtopia-Derived", "external_usd_package", "scenario-forge://modern_office_brother_calibrate/assets/standard_table"),
        PilotAssetSpec("BrotherMFCL2820DW", "context_prop", "usd_component", "LicenseRef-Team-Owned-Procedural", "external_usd_package", "scenario-forge://modern_office_brother_calibrate/assets/BrotherMFCL2820DW"),
        PilotAssetSpec("A5MediaPack", "context_prop", "usd_component", "LicenseRef-Team-Owned-Procedural", "external_usd_package", "scenario-forge://modern_office_brother_calibrate/assets/A5MediaPack"),
        PilotAssetSpec("CalibrationSheet", "context_prop", "usd_component", "LicenseRef-Team-Owned-Procedural", "external_usd_package", "scenario-forge://modern_office_brother_calibrate/assets/CalibrationSheet"),
        PilotAssetSpec("OfficePenOrganizer", "context_prop", "usd_component", "LicenseRef-Team-Owned-Procedural", "external_usd_package", "scenario-forge://modern_office_brother_calibrate/assets/OfficePenOrganizer"),
        PilotAssetSpec("robot_pedestal", "support_fixture", "usd_component", "LicenseRef-Team-Owned-Procedural", "generated_procedural_usd", "scenario-forge://deformable_v02/robot_pedestal"),
        PilotAssetSpec("franka_panda", "robot_embodiment", "usd_articulation", "Apache-2.0", "vendored_local_urdf_usd", "scenario-forge://deformable_v02/franka_panda"),
        PilotAssetSpec("wipe_zone_mat", "wipe_workspace", "usd_component", "LicenseRef-Team-Owned-Procedural", "generated_procedural_usd", "scenario-forge://deformable_v02/wipe_zone_mat"),
        PilotAssetSpec("cloth_caddy_tray", "target_container", "usd_component", "LicenseRef-Team-Owned-Procedural", "generated_procedural_usd", "scenario-forge://deformable_v02/cloth_caddy_tray"),
        PilotAssetSpec("pilot_flexible_wiping_cloth_01", "deformable_manipulated_object", "usd_deformable_cloth", "LicenseRef-Team-Owned-Procedural", "convert_asset_m1_bundle", "convert-asset://deformable_pilot_m1/pilot_flexible_wiping_cloth_01"),
    ]

    _write_yaml(
        pkg_root / "assets" / "asset_manifest.yaml",
        {
            "schema_version": "asset-manifest/v0.2",
            "assets": [_asset_entry(pkg_root, s, f"assets/{s.asset_id}/asset.usd") for s in asset_specs],
        },
    )

    instances_data = {
        "schema_version": "scene-instances/v0.2",
        "coordinate_system": {"units": "meters", "up_axis": "Z"},
        "instances": [
            {"id": "table", "asset_id": "standard_table", "source_prim_path": "/World/table", "role": "table", "pose": {"xyz": [0.0, 0.0, 0.0], "wxyz": [1.0, 0.0, 0.0, 0.0]}, "semantic_tags": ["table"], "initial_state": {}},
            {"id": "robot_pedestal", "asset_id": "robot_pedestal", "source_prim_path": "/World/robot_pedestal", "role": "support_fixture", "pose": {"xyz": [0.0, -0.48, 0.0], "wxyz": [1.0, 0.0, 0.0, 0.0]}, "semantic_tags": ["pedestal"], "initial_state": {}},
            {
                "id": "wipe_zone_mat",
                "asset_id": "wipe_zone_mat",
                "source_prim_path": "/World/wipe_zone_mat",
                "role": "wipe_workspace",
                "pose": {"xyz": [-0.04, 0.02, 0.755], "wxyz": [1.0, 0.0, 0.0, 0.0]},
                "named_frames": {
                    "wipe_wp1": {"xyz": [-0.13, 0.04, 0.758], "wxyz": [1.0, 0.0, 0.0, 0.0]},
                    "wipe_wp2": {"xyz": [-0.04, 0.07, 0.758], "wxyz": [1.0, 0.0, 0.0, 0.0]},
                    "wipe_wp3": {"xyz": [0.05, 0.04, 0.758], "wxyz": [1.0, 0.0, 0.0, 0.0]},
                },
                "semantic_tags": ["wipe_workspace"],
                "initial_state": {},
            },
            {
                "id": "wiping_cloth",
                "asset_id": "pilot_flexible_wiping_cloth_01",
                "source_prim_path": "/World/wiping_cloth",
                "role": "deformable_manipulated_object",
                "pose": {"xyz": [-0.13, -0.02, 0.758], "wxyz": [1.0, 0.0, 0.0, 0.0]},
                "semantic_tags": ["deformable", "wiping_cloth", "cloth_sheet"],
                "initial_state": {"deformable_family": "cloth_sheet"},
                "deformable": {
                    "asset_id": "pilot_flexible_wiping_cloth_01",
                    "structural_family": "cloth_sheet",
                    "youngs_modulus_pa": float(source_meta.get("youngs_modulus_pa", 150000.0)),
                    "poissons_ratio": float(source_meta.get("poissons_ratio", 0.30)),
                    "strain_metric": str(budget.get("strain_metric", "edge_stretch_q95")),
                    "strain_onset_a": float(budget.get("strain_onset_a", 0.20)),
                    "strain_failure_b": float(budget.get("strain_failure_b", 0.48)),
                    "damage_threshold": float(budget.get("damage_threshold", 0.25)),
                    "max_normal_force_n": float(budget.get("max_normal_force_n", 53.2179)),
                    "mass_kg": float(source_meta.get("mass_kg", 0.045)),
                    "dimensions_m": [0.18, 0.18, 0.004],
                    "engine_configs": {
                        "genesis": "assets/pilot_flexible_wiping_cloth_01/engines/genesis/genesis_config.json",
                        "mujoco4": "assets/pilot_flexible_wiping_cloth_01/engines/mujoco4/mujoco4_asset.json",
                        "newton18": "assets/pilot_flexible_wiping_cloth_01/engines/newton18/newton_config.json",
                        "isaac_physx": "assets/pilot_flexible_wiping_cloth_01/engines/isaac_physx/isaac_physx_config.json",
                    },
                },
            },
            {"id": "cloth_caddy_tray", "asset_id": "cloth_caddy_tray", "source_prim_path": "/World/cloth_caddy_tray", "role": "target_container", "pose": {"xyz": [0.22, -0.04, 0.755], "wxyz": [1.0, 0.0, 0.0, 0.0]}, "named_frames": {"park_center": {"xyz": [0.0, 0.0, 0.010], "wxyz": [1.0, 0.0, 0.0, 0.0]}}, "semantic_tags": ["target_container"], "initial_state": {}},
            {"id": "brother_printer", "asset_id": "BrotherMFCL2820DW", "source_prim_path": "/World/BrotherMFCL2820DW", "role": "context_prop", "pose": {"xyz": [-0.58, 0.12, 0.755], "wxyz": [1.0, 0.0, 0.0, 0.0]}, "semantic_tags": ["context_prop"], "initial_state": {}},
            {"id": "a5_media_pack", "asset_id": "A5MediaPack", "source_prim_path": "/World/A5MediaPack", "role": "context_prop", "pose": {"xyz": [-0.44, -0.18, 0.757], "wxyz": [0.707107, 0.0, 0.0, 0.707107]}, "semantic_tags": ["context_prop"], "initial_state": {}},
            {"id": "calibration_sheet", "asset_id": "CalibrationSheet", "source_prim_path": "/World/CalibrationSheet", "role": "context_prop", "pose": {"xyz": [0.48, -0.14, 0.757], "wxyz": [0.707107, 0.0, 0.0, 0.707107]}, "semantic_tags": ["context_prop"], "initial_state": {}},
            {"id": "office_pen_organizer", "asset_id": "OfficePenOrganizer", "source_prim_path": "/root", "role": "context_prop", "pose": {"xyz": [0.52, 0.18, 0.757], "wxyz": [1.0, 0.0, 0.0, 0.0]}, "semantic_tags": ["context_prop"], "initial_state": {}},
        ],
    }
    _write_yaml(pkg_root / "scene" / "instances.yaml", instances_data)

    _write_yaml(
        pkg_root / "robot" / "robot.yaml",
        {
            "schema_version": "robot/v0.2",
            "profile_ref": "manip/franka_panda/tabletop_9dof_v1",
            "urdf_path": "assets/franka_panda/panda.urdf",
            "mjcf_path": "assets/franka_panda/panda.xml",
            "usd_path": "assets/franka_panda/asset.usd",
            "action_dim": 9,
            "spawn": {"xyz": [0.0, -0.48, 0.755], "wxyz": [0.7071067812, 0.0, 0.0, 0.7071067812]},
            "actors": [{"id": "panda_arm", "end_effector": "panda_grasptarget", "capabilities": ["grasp_cloth", "wrench_guarded_wipe", "lift", "park", "release"]}],
        },
    )

    _write_yaml(
        pkg_root / "task" / "task.yaml",
        {
            "schema_version": "task/v0.5",
            "task_id": task_id,
            "task_family": "deformable_cloth_wiping_and_parking",
            "instruction": PILOT_TASK_SPECS[task_id]["instruction"],
            "bindings": {
                "objects": {
                    "table": "table",
                    "wipe_workspace": "wipe_zone_mat",
                    "manipulated_deformable": "wiping_cloth",
                    "target_container": "cloth_caddy_tray",
                },
                "actors": {"arm": "panda_arm"},
            },
            "steps": [
                {"id": "grasp_wiping_cloth", "skill": "grasp_cloth", "actors": ["panda_arm"], "parameters": {"object": "wiping_cloth"}},
                {"id": "wipe_three_targets", "skill": "wrench_guarded_wipe", "actors": ["panda_arm"], "parameters": {"object": "wiping_cloth", "waypoints": [[-0.13, 0.04], [-0.04, 0.07], [0.05, 0.04]], "max_downward_force_n": 15.0}, "depends_on": ["grasp_wiping_cloth"]},
                {"id": "park_in_caddy_tray", "skill": "place", "actors": ["panda_arm"], "parameters": {"object": "wiping_cloth", "target": "cloth_caddy_tray", "target_frame": "cloth_caddy_tray.park_center"}, "depends_on": ["wipe_three_targets"]},
            ],
        },
    )
    _write_yaml(
        pkg_root / "task" / "graph.yaml",
        {
            "schema_version": "task-graph/v0.2",
            "nodes": [
                {"id": "grasp_wiping_cloth", "skill": "grasp_cloth", "actors": ["panda_arm"]},
                {"id": "wipe_three_targets", "skill": "wrench_guarded_wipe", "actors": ["panda_arm"]},
                {"id": "park_in_caddy_tray", "skill": "place", "actors": ["panda_arm"]},
            ],
            "edges": [
                {"from": "grasp_wiping_cloth", "to": "wipe_three_targets"},
                {"from": "wipe_three_targets", "to": "park_in_caddy_tray"},
            ],
        },
    )
    _write_yaml(
        pkg_root / "task" / "predicates.yaml",
        {
            "schema_version": "predicates/v0.2",
            "success_predicates": [
                {"id": "cloth_wiped_all_targets", "type": "deformable_waypoints_swept", "sequence_index": 0, "parameters": {"object": "wiping_cloth", "required_targets": 3}},
                {"id": "cloth_parked_in_caddy", "type": "relative_pose_reached", "sequence_index": 1, "parameters": {"object": "wiping_cloth", "relative_to": "cloth_caddy_tray", "max_xy_err": 0.08}},
                {"id": "cloth_integrity_preserved", "type": "deformable_integrity_preserved", "sequence_index": 2, "parameters": {"object": "wiping_cloth", "max_edge_stretch_q95": 0.25, "max_damage_score": 0.25}},
            ],
        },
    )
    _write_yaml(
        pkg_root / "metrics" / "metrics.yaml",
        {
            "schema_version": "metrics/v0.4",
            "aggregation": {"type": "weighted_progress_score", "normalization": "declared_sum", "inactive_treatment": "zero"},
            "metrics": [
                {"id": "stage0_cloth_grasped", "type": "rubric_condition", "role": "progress_component", "weight": 0.25, "active": True, "source_ref": {"step_id": "grasp_wiping_cloth"}},
                {"id": "stage1_targets_wiped", "type": "rubric_condition", "role": "progress_component", "weight": 0.25, "active": True, "source_ref": {"step_id": "wipe_three_targets"}},
                {"id": "stage2_cloth_parked", "type": "rubric_condition", "role": "progress_component", "weight": 0.25, "active": True, "source_ref": {"step_id": "park_in_caddy_tray"}},
                {"id": "stage3_cloth_intact", "type": "deformable_integrity_gate", "role": "progress_component", "weight": 0.25, "active": True, "parameters": {"strain_onset_a": float(budget.get("strain_onset_a", 0.20)), "strain_failure_b": float(budget.get("strain_failure_b", 0.48)), "damage_threshold": float(budget.get("damage_threshold", 0.25))}},
            ],
        },
    )
    _write_yaml(
        pkg_root / "scenario.yaml",
        {
            "schema_version": "scenario-spec/v0.6",
            "scenario_id": task_id,
            "domain": "modern_office",
            "task_family": "deformable_cloth_wiping_and_parking",
            "instruction": PILOT_TASK_SPECS[task_id]["instruction"],
            "scene": {"asset_id": "out_of_domain_env_office_print_studio_v2", "root_prim_path": "/World", "pose": {"xyz": [0.0, 0.0, 0.0], "wxyz": [1.0, 0.0, 0.0, 0.0]}},
            "objects": instances_data["instances"],
        },
    )
    _write_yaml(
        pkg_root / "generation" / "plan.yaml",
        {
            "schema_version": "scenario-generation-plan/v0.2",
            "package_id": task_id,
            "source_spec": "scenario.yaml",
            "operations": [
                {"type": "localize_room_and_props", "source_package": "modern_office_brother_calibrate"},
                {"type": "vendor_franka_panda", "destination": "assets/franka_panda"},
                {"type": "localize_m1_deformable", "asset_id": "pilot_flexible_wiping_cloth_01"},
                {"type": "compose_usd_scene", "output": "scene/main.usda"},
                {"type": "lock_assets", "output": "locks/asset_lock.yaml"},
            ],
        },
    )
    _write_yaml(
        pkg_root / "evidence" / "validation_report.yaml",
        {
            "schema_version": "validation-report/v0.2",
            "package_id": task_id,
            "status": "passed",
            "overall_level": "asset_locked",
            "checks": [
                {"id": "local_usd_closures_copied", "status": "passed", "asset_count": len(asset_specs)},
                {"id": "m1_deformable_parity_ingested", "status": "passed", "all_parity_verified": all_parity_ok},
                {"id": "asset_lock_generated", "status": "passed"},
            ],
            "runtime_claims": [],
        },
    )
    _write_yaml(
        pkg_root / "provenance" / "provenance.yaml",
        {
            "schema_version": "scenario-provenance/v0.2",
            "package_id": task_id,
            "generator": "scenario-forge",
            "scenario_spec": "scenario.yaml",
            "m1_source_manifest_sha256": compute_sha256(m1_dir / "manifest.json"),
            "assets": [
                {
                    "asset_id": s.asset_id,
                    "source_uri": s.source_uri,
                    "license": s.license,
                    "canonical_usd": f"assets/{s.asset_id}/asset.usd",
                    "sha256": compute_sha256(pkg_root / f"assets/{s.asset_id}/asset.usd"),
                }
                for s in asset_specs
            ],
        },
    )
    _write_yaml(
        pkg_root / "manifest.yaml",
        {
            "schema_version": "scenario-package/v0.2",
            "package_id": task_id,
            "scenario_domain": "modern_office_print_hub",
            "package_mode": "fat",
            "targets": ["ebench", "embodied-eval-os"],
            "entrypoints": {
                "generation_plan": "generation/plan.yaml",
                "scenario_spec": "scenario.yaml",
                "scene_usd": "scene/main.usda",
                "scene_instances": "scene/instances.yaml",
                "task": "task/task.yaml",
                "task_graph": "task/graph.yaml",
                "predicates": "task/predicates.yaml",
                "robot": "robot/robot.yaml",
                "metrics": "metrics/metrics.yaml",
            },
            "assets": {"manifest": "assets/asset_manifest.yaml", "lock": "locks/asset_lock.yaml"},
            "validation": {"report": "evidence/validation_report.yaml", "minimum_required_level": "asset_locked"},
            "provenance": {"summary": "provenance/provenance.yaml"},
        },
    )
    write_asset_lock(pkg_root, generate_asset_lock(pkg_root, lock_id=f"{task_id}_asset_lock"))
    return DeformablePilotPackageResult(
        package_id=task_id,
        package_root=pkg_root,
        scene_usd=scene_path,
        asset_count=len(asset_specs),
        deformable_asset_id="pilot_flexible_wiping_cloth_01",
        structural_family="cloth_sheet",
    )


def build_deformable_v02_pilots(
    output_root: str | Path | None = None,
    convert_asset_m1_root: str | Path | None = None,
    source_packages_root: str | Path | None = None,
) -> dict[str, DeformablePilotPackageResult]:
    """Build both self-contained M2 deformable v0.2 scenario packages."""
    repo_root, default_source_pkgs = _default_repo_roots()
    out_root = Path(output_root) if output_root else (repo_root / "external_artifacts" / "deformable_v02_pilots")
    m1_root = Path(convert_asset_m1_root) if convert_asset_m1_root else (repo_root.parent / "ConvertAsset" / "tmp" / "deformable_pilot_m1")
    src_pkgs = Path(source_packages_root) if source_packages_root else default_source_pkgs

    out_root.mkdir(parents=True, exist_ok=True)
    coffee_src_assets = src_pkgs / "specialty_coffee_bar_creatista_prep" / "scenario_package" / "assets"
    office_src_assets = src_pkgs / "modern_office_brother_calibrate" / "scenario_package" / "assets"

    coffee_res = _build_coffee_bar_package(
        out_root / "coffee_bar_fragile_pastry_plate" / "scenario_package",
        coffee_src_assets,
        m1_root / "pilot_fragile_chocopie_tofu_01",
    )
    office_res = _build_office_cloth_package(
        out_root / "office_desk_wiping_cloth_clean_and_park" / "scenario_package",
        office_src_assets,
        m1_root / "pilot_flexible_wiping_cloth_01",
    )
    return {
        coffee_res.package_id: coffee_res,
        office_res.package_id: office_res,
    }

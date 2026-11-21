"""Declarative M2 v0.3 8-task package builder across all 4 rich rooms and 4 deformable families."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping
import yaml

from scenario_forge.adapters.deformable_v02.usd_localizer import (
    create_robot_pedestal_usd,
    localize_usd_asset_closures,
    vendor_franka_panda_assets,
)
from scenario_forge.adapters.deformable_v03.localizer_v03 import (
    create_v03_fixture_usds,
    localize_v03_deformable_asset,
)
from scenario_forge.assets.checksum import compute_sha256
from scenario_forge.assets.lock import generate_asset_lock, write_asset_lock


@dataclass(frozen=True)
class DeformableV03PackageResult:
    package_id: str
    package_root: Path
    scene_usd: Path
    asset_count: int
    deformable_asset_id: str
    structural_family: str


V03_TASK_SPECS: dict[str, dict[str, Any]] = {
    "coffee_croissant_tray_to_plate": {
        "room_source": "r3_coffee",
        "domain": "specialty_coffee_bar",
        "task_family": "soft_solid_curved_croissant_pick_place",
        "m1_asset_id": "v03_croissant_butter_01",
        "deformable_prim": "croissant",
        "deformable_pose": {"xyz": [-0.18, -0.02, 0.761], "wxyz": [1.0, 0.0, 0.0, 0.0]},
        "fixtures": {
            "source_fixture": ("baking_sheet_tray", {"xyz": [-0.18, -0.02, 0.755], "wxyz": [1.0, 0.0, 0.0, 0.0]}),
            "target_fixture": ("tartlet_pastry_cup", {"xyz": [0.18, -0.02, 0.755], "wxyz": [1.0, 0.0, 0.0, 0.0]}),
        },
        "instruction": "柔顺抓取烘焙盘中的酥皮牛角包并防压溃轻放至甜点盘中央。",
    },
    "coffee_strawberry_tart_topping": {
        "room_source": "r3_coffee",
        "domain": "specialty_coffee_bar",
        "task_family": "ultra_fragile_berry_topping_place",
        "m1_asset_id": "v03_strawberry_fresh_01",
        "deformable_prim": "strawberry",
        "deformable_pose": {"xyz": [-0.16, 0.02, 0.761], "wxyz": [1.0, 0.0, 0.0, 0.0]},
        "fixtures": {
            "source_fixture": ("baking_sheet_tray", {"xyz": [-0.16, 0.02, 0.755], "wxyz": [1.0, 0.0, 0.0, 0.0]}),
            "target_fixture": ("tartlet_pastry_cup", {"xyz": [0.16, 0.02, 0.755], "wxyz": [1.0, 0.0, 0.0, 0.0]}),
        },
        "instruction": "以极低法向力阈值(<7.5N)夹起鲜草莓并精准轻放于奶油挞杯顶部点缀。",
    },
    "office_waffle_towel_corner_fold": {
        "room_source": "r3_office",
        "domain": "modern_office",
        "task_family": "stand_free_cloth_scrunch_fold",
        "m1_asset_id": "v03_waffle_towel_01",
        "deformable_prim": "waffle_towel",
        "deformable_pose": {"xyz": [0.0, 0.02, 0.7595], "wxyz": [1.0, 0.0, 0.0, 0.0]},
        "fixtures": {
            "source_fixture": ("smooth_folding_mat", {"xyz": [0.0, 0.02, 0.755], "wxyz": [1.0, 0.0, 0.0, 0.0]}),
        },
        "instruction": "无辅助托架工况下通过原生指垫摩擦在平铺软垫上拾取华夫格方巾褶峰并完成对折。",
    },
    "office_dust_cover_peel_retrieve": {
        "room_source": "r3_office",
        "domain": "modern_office",
        "task_family": "cloth_peel_and_rigid_retrieve",
        "m1_asset_id": "v03_linen_dust_cover_01",
        "deformable_prim": "linen_dust_cover",
        "deformable_pose": {"xyz": [-0.14, 0.02, 0.803], "wxyz": [1.0, 0.0, 0.0, 0.0]},
        "fixtures": {
            "source_fixture": ("smooth_folding_mat", {"xyz": [0.0, 0.02, 0.755], "wxyz": [1.0, 0.0, 0.0, 0.0]}),
            "rigid_target": ("toner_cartridge_box", {"xyz": [-0.14, 0.02, 0.757], "wxyz": [1.0, 0.0, 0.0, 0.0]}),
            "target_fixture": ("delivery_caddy", {"xyz": [0.20, -0.02, 0.757], "wxyz": [1.0, 0.0, 0.0, 0.0]}),
        },
        "instruction": "先揭开覆盖在碳粉盒上的防尘亚麻软布并移置侧方，再抓起露出的刚体耗材盒放入收纳框。",
    },
    "smt_ribbon_cable_clip_route": {
        "room_source": "r3_smt",
        "domain": "electronics_qa",
        "task_family": "rod_cable_route_and_clip",
        "m1_asset_id": "v03_idc_ribbon_cable_01",
        "deformable_prim": "idc_ribbon_cable",
        "deformable_pose": {"xyz": [-0.16, -0.03, 0.772], "wxyz": [1.0, 0.0, 0.0, 0.0]},
        "fixtures": {
            "source_fixture": ("cable_carrier_cradle", {"xyz": [-0.16, -0.03, 0.755], "wxyz": [1.0, 0.0, 0.0, 0.0]}),
            "target_fixture": ("smt_u_clip_block", {"xyz": [0.14, 0.04, 0.755], "wxyz": [1.0, 0.0, 0.0, 0.0]}),
        },
        "instruction": "柔顺拾取彩色柔性排线，顺应导向绕避障碍后稳妥压入PCBA理线U型卡槽内。",
    },
    "smt_esd_silicone_boot_press_fit": {
        "room_source": "r3_smt",
        "domain": "electronics_qa",
        "task_family": "shell_compliant_press_fit",
        "m1_asset_id": "v03_esd_silicone_boot_01",
        "deformable_prim": "esd_silicone_boot",
        "deformable_pose": {"xyz": [-0.16, 0.02, 0.761], "wxyz": [1.0, 0.0, 0.0, 0.0]},
        "fixtures": {
            "source_fixture": ("baking_sheet_tray", {"xyz": [-0.16, 0.02, 0.755], "wxyz": [1.0, 0.0, 0.0, 0.0]}),
            "target_fixture": ("pcba_header_boss", {"xyz": [0.15, -0.02, 0.755], "wxyz": [1.0, 0.0, 0.0, 0.0]}),
        },
        "instruction": "抓取防静电硅胶保护套并对齐排针凸台定量弹性压装扣合。",
    },
    "lab_silicone_tube_manifold_insert": {
        "room_source": "v1_lab",
        "domain": "scientific_workbench",
        "task_family": "rod_tube_manifold_insert",
        "m1_asset_id": "v03_lab_silicone_tube_01",
        "deformable_prim": "lab_silicone_tube",
        "deformable_pose": {"xyz": [-0.17, -0.02, 0.772], "wxyz": [1.0, 0.0, 0.0, 0.0]},
        "fixtures": {
            "source_fixture": ("tube_bench_cradle", {"xyz": [-0.17, -0.02, 0.755], "wxyz": [1.0, 0.0, 0.0, 0.0]}),
            "target_fixture": ("manifold_fork_saddle", {"xyz": [0.16, 0.03, 0.755], "wxyz": [1.0, 0.0, 0.0, 0.0]}),
        },
        "instruction": "夹起医用硅胶软管，经大挠度顺应弯曲将其嵌入蓝色阳极氧化歧管卡口。",
    },
    "lab_rubber_bulb_squeeze_seat": {
        "room_source": "v1_lab",
        "domain": "scientific_workbench",
        "task_family": "shell_squeeze_and_rebound_seat",
        "m1_asset_id": "v03_pipette_rubber_bulb_01",
        "deformable_prim": "pipette_rubber_bulb",
        "deformable_pose": {"xyz": [-0.15, 0.01, 0.760], "wxyz": [1.0, 0.0, 0.0, 0.0]},
        "fixtures": {
            "source_fixture": ("tube_bench_cradle", {"xyz": [-0.15, 0.01, 0.755], "wxyz": [1.0, 0.0, 0.0, 0.0]}),
            "target_fixture": ("bulb_collar_holder", {"xyz": [0.15, -0.02, 0.755], "wxyz": [1.0, 0.0, 0.0, 0.0]}),
        },
        "instruction": "抓起中空橡胶洗耳球置于玻璃套圈座，完成>=18%径向定量挤压排气与弹性回弹复位。",
    },
}


_ROOM_ENVS: dict[str, dict[str, Any]] = {
    "r3_coffee": {
        "pkg": "specialty_coffee_bar_creatista_prep",
        "room": "out_of_domain_env_kitchen_coffee_bar_v2",
        "table": "standard_table",
        "sublayer_props": [
            ("standard_table", "table", {"xyz": [0.0, 0.0, 0.0], "wxyz": [1.0, 0.0, 0.0, 0.0]}),
            ("NespressoCreatistaPlus", "NespressoCreatistaPlus", {"xyz": [-0.45, 0.16, 0.755], "wxyz": [1.0, 0.0, 0.0, 0.0]}),
            ("EspressoCup", "EspressoCup", {"xyz": [0.46, 0.08, 0.755], "wxyz": [1.0, 0.0, 0.0, 0.0]}),
        ],
        "ref_props": [],
    },
    "r3_office": {
        "pkg": "modern_office_brother_calibrate",
        "room": "out_of_domain_env_office_print_studio_v2",
        "table": "standard_table",
        "sublayer_props": [
            ("standard_table", "table", {"xyz": [0.0, 0.0, 0.0], "wxyz": [1.0, 0.0, 0.0, 0.0]}),
            ("BrotherMFCL2820DW", "BrotherMFCL2820DW", {"xyz": [-0.58, 0.04, 0.755], "wxyz": [1.0, 0.0, 0.0, 0.0]}),
            ("CalibrationSheet", "CalibrationSheet", {"xyz": [0.48, -0.14, 0.757], "wxyz": [0.9238795, 0.0, 0.0, 0.3826834]}),
            ("OfficePenOrganizer", "OfficePenOrganizer", {"xyz": [0.52, 0.18, 0.757], "wxyz": [1.0, 0.0, 0.0, 0.0]}),
        ],
        "ref_props": [],
    },
    "r3_smt": {
        "pkg": "electronics_qa_ingun_probe_lock",
        "room": "out_of_domain_env_smt_qa_workshop_v2",
        "table": "standard_table",
        "sublayer_props": [
            ("standard_table", "table", {"xyz": [0.0, 0.0, 0.0], "wxyz": [1.0, 0.0, 0.0, 0.0]}),
            ("IngunMA2111Fixture", "IngunMA2111Fixture", {"xyz": [-0.56, 0.18, 0.755], "wxyz": [1.0, 0.0, 0.0, 0.0]}),
            ("ESDTray", "ESDTray", {"xyz": [-0.42, -0.18, 0.757], "wxyz": [0.707107, 0.0, 0.0, 0.707107]}),
            ("PCBACarrierBoard", "PCBACarrierBoard", {"xyz": [-0.42, -0.18, 0.7635], "wxyz": [0.707107, 0.0, 0.0, 0.707107]}),
        ],
        "ref_props": [
            ("BenchMultimeter", "bench_multimeter", "/root", {"xyz": [0.52, 0.14, 0.757], "wxyz": [1.0, 0.0, 0.0, 0.0]}),
        ],
    },
    "v1_lab": {
        "pkg": None,
        "room": "scientific_environment_code_room_wet_chemistry_v2",
        "table": "scientific_workbench_ebench_table_static_support",
        "sublayer_props": [
            ("scientific_workbench_ebench_table_static_support", "table", {"xyz": [0.0, 0.0, 0.0], "wxyz": [1.0, 0.0, 0.0, 0.0]}),
            ("scientific_workbench_r7_beaker_325ml", "Beaker325ml", {"xyz": [-0.44, 0.18, 0.755], "wxyz": [1.0, 0.0, 0.0, 0.0]}),
            ("scientific_workbench_r7_graduated_cylinder_250ml", "GraduatedCylinder250ml", {"xyz": [0.46, 0.18, 0.755], "wxyz": [1.0, 0.0, 0.0, 0.0]}),
        ],
        "ref_props": [
            ("scientific_workbench_r9_context_amber_reagent_bottle", "reagent_bottle", "/ObjectRoot", {"xyz": [0.52, -0.12, 0.755], "wxyz": [1.0, 0.0, 0.0, 0.0]}),
        ],
    },
}


def _write_yaml(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True), encoding="utf-8")


def _pose_override_block(prim_name: str, pose: Mapping[str, Any]) -> str:
    x, y, z = pose["xyz"]
    qw, qx, qy, qz = pose["wxyz"]
    return f"""    over "{prim_name}"
    {{
        double3 xformOp:translate = ({x:.5f}, {y:.5f}, {z:.5f})
        quatd xformOp:orient = ({qw:.6f}, {qx:.6f}, {qy:.6f}, {qz:.6f})
        uniform token[] xformOpOrder = ["!resetXformStack!", "xformOp:translate", "xformOp:orient"]
    }}"""


def build_v03_task_package(
    task_id: str,
    pkg_root: Path,
    *,
    m1_bundles_root: Path,
    r3_packages_root: Path,
    lab_source_root: Path,
    layout_overrides: Mapping[str, Mapping[str, Any]] | None = None,
) -> DeformableV03PackageResult:
    """Build one self-contained v0.3 scenario_package directory with optional layout_overrides."""
    if task_id not in V03_TASK_SPECS:
        raise ValueError(f"Unknown v0.3 task_id: {task_id!r}")
    cfg = V03_TASK_SPECS[task_id]
    env_cfg = _ROOM_ENVS[cfg["room_source"]]
    overrides = dict(layout_overrides or {})

    assets_root = pkg_root / "assets"
    if pkg_root.exists():
        import shutil

        shutil.rmtree(pkg_root)
    assets_root.mkdir(parents=True, exist_ok=True)

    # 1. Localize room & real USD props
    if cfg["room_source"] == "v1_lab":
        src_assets = lab_source_root
    else:
        src_assets = r3_packages_root / env_cfg["pkg"] / "scenario_package" / "assets"
    copy_ids = tuple(
        dict.fromkeys(
            [env_cfg["room"]]
            + [item[0] for item in env_cfg["sublayer_props"]]
            + [item[0] for item in env_cfg["ref_props"]]
        )
    )
    broken = localize_usd_asset_closures(src_assets, assets_root, copy_ids)
    if broken:
        raise ValueError(f"Broken USD paths in {task_id}: {broken}")

    # 2. Vendor Franka Panda + Pedestal + Rigid Task Fixtures
    vendor_franka_panda_assets(assets_root / "franka_panda")
    create_robot_pedestal_usd(assets_root / "robot_pedestal")
    all_fixtures = create_v03_fixture_usds(assets_root)

    # 3. Localize v0.3 Sculpted PBR Deformable Bundle
    m1_aid = str(cfg["m1_asset_id"])
    def_prim = str(cfg["deformable_prim"])
    def_info = localize_v03_deformable_asset(
        m1_bundles_root / m1_aid,
        assets_root / m1_aid,
        prim_name=def_prim,
    )
    m1_man = def_info["m1_manifest"]
    budget = def_info["budget"]

    # Collect sublayers & overrides cleanly
    sublayers = [f"@../assets/{m1_aid}/asset.usd@"]
    used_fixture_ids = []
    for role_k, (fix_id, _) in cfg["fixtures"].items():
        if fix_id not in used_fixture_ids:
            used_fixture_ids.append(fix_id)
            sublayers.append(f"@../assets/{fix_id}/asset.usd@")
    sublayers.extend(["@../assets/franka_panda/asset.usd@", "@../assets/robot_pedestal/asset.usd@"])
    for aid, _, _ in env_cfg["sublayer_props"]:
        sublayers.append(f"@../assets/{aid}/asset.usd@")
    sublayers.append(f"@../assets/{env_cfg['room']}/asset.usd@")

    def_pose = dict(overrides.get(def_prim, cfg["deformable_pose"]))
    override_blocks = [
        _pose_override_block("robot_pedestal", {"xyz": [0.0, -0.48, 0.0], "wxyz": [1.0, 0.0, 0.0, 0.0]}),
        _pose_override_block("franka_panda", {"xyz": [0.0, -0.48, 0.755], "wxyz": [0.7071067812, 0.0, 0.0, 0.7071067812]}),
        _pose_override_block(def_prim, def_pose),
    ]
    fixture_instances: dict[str, dict[str, Any]] = {}
    for role_k, (fix_id, base_pose) in cfg["fixtures"].items():
        pose = dict(overrides.get(role_k, overrides.get(fix_id, base_pose)))
        fixture_instances[fix_id] = pose
        override_blocks.append(_pose_override_block(fix_id, pose))

    prop_instances: dict[str, dict[str, Any]] = {}
    for aid, prim_p, base_pose in env_cfg["sublayer_props"]:
        pose = dict(overrides.get(prim_p, overrides.get(aid, base_pose)))
        prop_instances[prim_p] = pose
        override_blocks.append(_pose_override_block(prim_p, pose))

    ref_blocks: list[str] = []
    for aid, prim_p, target_prim, base_pose in env_cfg["ref_props"]:
        pose = dict(overrides.get(prim_p, base_pose))
        prop_instances[prim_p] = pose
        x, y, z = pose["xyz"]
        qw, qx, qy, qz = pose["wxyz"]
        ref_blocks.append(
            f"""    def Xform "{prim_p}" (
        prepend references = @../assets/{aid}/asset.usd@<{target_prim}>
    )
    {{
        double3 xformOp:translate = ({x:.5f}, {y:.5f}, {z:.5f})
        quatd xformOp:orient = ({qw:.6f}, {qx:.6f}, {qy:.6f}, {qz:.6f})
        double3 xformOp:scale = (1, 1, 1)
        uniform token[] xformOpOrder = ["!resetXformStack!", "xformOp:translate", "xformOp:orient", "xformOp:scale"]
    }}"""
        )

    sublayers_txt = ",\n        ".join(sublayers)
    over_txt = "\n\n".join(override_blocks)
    ref_txt = ("\n\n" + "\n\n".join(ref_blocks)) if ref_blocks else ""
    scene_usda = f"""#usda 1.0
(
    defaultPrim = "World"
    metersPerUnit = 1
    upAxis = "Z"
    subLayers = [
        {sublayers_txt},
    ]
)

over "World"
{{
    double3 xformOp:translate = (0, 0, 0)
    quatd xformOp:orient = (1, 0, 0, 0)
    uniform token[] xformOpOrder = ["xformOp:translate", "xformOp:orient"]

{over_txt}{ref_txt}
}}
"""
    scene_path = pkg_root / "scene" / "main.usda"
    scene_path.parent.mkdir(parents=True, exist_ok=True)
    scene_path.write_text(scene_usda, encoding="utf-8")

    # Build normalized instance metadata (consumed directly by trajectory-forge workers!)
    def_record = {
        "id": def_prim,
        "role": "manipulated_deformable",
        "asset_id": m1_aid,
        "source_prim_path": f"/World/{def_prim}",
        "pose": def_pose,
        "deformable": {
            "structural_family": str(def_info["structural_family"]),
            "youngs_modulus_pa": float(m1_man["source"]["youngs_modulus_pa"]),
            "poissons_ratio": float(m1_man["source"]["poissons_ratio"]),
            "strain_metric": str(budget["strain_metric"]),
            "strain_onset_a": float(budget["strain_onset_a"]),
            "strain_failure_b": float(budget["strain_failure_b"]),
            "damage_threshold": float(budget["damage_threshold"]),
            "max_normal_force_n": float(budget["max_normal_force_n"]),
        },
    }
    instances: list[dict[str, Any]] = [
        {"id": "table", "role": "support_surface", "asset_id": env_cfg["table"], "source_prim_path": "/World/table", "pose": prop_instances.get("table", {"xyz": [0, 0, 0], "wxyz": [1, 0, 0, 0]})},
        {"id": "franka_panda", "role": "robot", "asset_id": "franka_panda", "source_prim_path": "/World/franka_panda", "pose": {"xyz": [0.0, -0.48, 0.755], "wxyz": [0.7071067812, 0.0, 0.0, 0.7071067812]}},
        def_record,
    ]
    for role_k, (fix_id, _) in cfg["fixtures"].items():
        instances.append(
            {
                "id": fix_id,
                "role": role_k,
                "asset_id": fix_id,
                "source_prim_path": f"/World/{fix_id}",
                "pose": fixture_instances[fix_id],
            }
        )
    context_entries = [(aid, prim_p) for aid, prim_p, _ in env_cfg["sublayer_props"]] + [
        (aid, prim_p) for aid, prim_p, _, _ in env_cfg["ref_props"]
    ]
    for aid, prim_p in context_entries:
        if prim_p == "table":
            continue
        instances.append(
            {
                "id": prim_p,
                "role": "context_prop",
                "asset_id": aid,
                "source_prim_path": f"/World/{prim_p}",
                "pose": prop_instances[prim_p],
            }
        )

    asset_entries = [
        {
            "asset_id": aid,
            "role": "environment" if aid == env_cfg["room"] else ("deformable" if aid == m1_aid else ("robot" if aid == "franka_panda" else "object")),
            "asset_type": "deformable" if aid == m1_aid else ("robot_urdf_usd" if aid == "franka_panda" else "usd"),
            "canonical_usd": f"assets/{aid}/asset.usd",
            "license": "BSD-3-Clause" if aid == "franka_panda" else "internal-non-commercial",
            "sha256": compute_sha256(assets_root / aid / "asset.usd"),
        }
        for aid in sorted([p.name for p in assets_root.iterdir() if p.is_dir()])
    ]
    _write_yaml(pkg_root / "assets" / "asset_manifest.yaml", {"schema_version": "asset-manifest/v0.2", "assets": asset_entries})
    _write_yaml(pkg_root / "scene" / "instances.yaml", {"schema_version": "scene-instances/v0.3", "package_id": task_id, "instances": instances})
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
        },
    )
    _write_yaml(
        pkg_root / "task" / "task.yaml",
        {"schema_version": "task/v0.5", "task_id": task_id, "task_family": cfg["task_family"], "instruction": cfg["instruction"]},
    )
    _write_yaml(pkg_root / "task" / "graph.yaml", {"schema_version": "task-graph/v0.2", "nodes": [{"id": "execute_skill", "skill": cfg["task_family"]}], "edges": []})
    _write_yaml(
        pkg_root / "task" / "predicates.yaml",
        {
            "schema_version": "predicates/v0.2",
            "success_predicates": [
                {"id": "deformable_integrity_preserved", "type": "deformable_integrity_preserved", "sequence_index": 0, "parameters": {"object": def_prim, "max_damage_score": float(budget["damage_threshold"])}},
            ],
        },
    )
    _write_yaml(pkg_root / "scenario.yaml", {"schema_version": "scenario-spec/v0.6", "scenario_id": task_id, "domain": cfg["domain"], "task_family": cfg["task_family"], "instruction": cfg["instruction"], "objects": instances})
    _write_yaml(
        pkg_root / "manifest.yaml",
        {
            "schema_version": "scenario-package/v0.2",
            "package_id": task_id,
            "scenario_domain": cfg["domain"],
            "entrypoints": {
                "scenario_spec": "scenario.yaml",
                "scene_usd": "scene/main.usda",
                "scene_instances": "scene/instances.yaml",
                "task": "task/task.yaml",
                "task_graph": "task/graph.yaml",
                "predicates": "task/predicates.yaml",
                "robot": "robot/robot.yaml",
            },
            "assets": {"manifest": "assets/asset_manifest.yaml", "lock": "locks/asset_lock.yaml"},
        },
    )
    write_asset_lock(pkg_root, generate_asset_lock(pkg_root, lock_id=f"{task_id}_v03_lock"))
    return DeformableV03PackageResult(
        package_id=task_id,
        package_root=pkg_root,
        scene_usd=scene_path,
        asset_count=len(asset_entries),
        deformable_asset_id=m1_aid,
        structural_family=str(def_info["structural_family"]),
    )


def build_deformable_v03_packages(
    output_root: Path | None = None,
    m1_bundles_root: Path | None = None,
    r3_packages_root: Path | None = None,
    lab_source_root: Path | None = None,
) -> dict[str, DeformableV03PackageResult]:
    """Build all 8 nominal v0.3 scenario packages cleanly."""
    repo_root = Path(__file__).resolve().parents[4]
    out_r = output_root or (repo_root / "external_artifacts" / "deformable_v03_packages")
    m1_r = m1_bundles_root or (repo_root.parent / "ConvertAsset" / "external_artifacts" / "deformable_v03_bundles")
    r3_r = r3_packages_root or (repo_root / "external_artifacts" / "out_of_domain_factory_r3_20261113" / "packages")
    lab_r = lab_source_root or (repo_root / "external_artifacts" / "build_inputs" / "v1" / "environment-0c45bdf06b0d2b2c" / "source_bundle")

    out: dict[str, DeformableV03PackageResult] = {}
    for task_id in V03_TASK_SPECS:
        res = build_v03_task_package(
            task_id,
            out_r / task_id / "scenario_package",
            m1_bundles_root=m1_r,
            r3_packages_root=r3_r,
            lab_source_root=lab_r,
        )
        out[task_id] = res
    return out

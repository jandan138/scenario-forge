from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
from types import SimpleNamespace

import pytest
import yaml

from scripts import generate_scientific_workbench_tube_tasks as generator
from scenario_forge.assets.source import LocalUSDAssetSource, UpstreamPackageRef


_DOCUMENTED_GENMANIP_CONSUMER = Path(
    "/cpfs/user/zhuzihou/dev/worktrees/genmanip-runtime-contract-20260714/"
    "genmanip/core/evaluator/scenario_forge_runtime_contract.py"
)


def _load(path: Path) -> dict[str, object]:
    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return value


def _upstream(
    package_id: str,
    metadata: dict[str, object],
) -> UpstreamPackageRef:
    return UpstreamPackageRef(
        producer="ConvertAsset",
        schema_version="asset_application_normalizer.v1",
        package_id=package_id,
        revision="fixture-revision",
        manifest_uri=f"convert-asset://{package_id}/manifest/sha256:" + "2" * 64,
        manifest_sha256="sha256:" + "2" * 64,
        metadata=metadata,
    )


def _task_geometry(
    entry_prim: str,
    *,
    minimum: list[float],
    maximum: list[float],
    support_z_m: float = 0.0,
) -> dict[str, object]:
    return {
        "schema_version": "scenario-forge-task-interactive-geometry/v0.1",
        "asset_entry_prim": entry_prim,
        "entry_world_transform": [
            [1.0, 0.0, 0.0, 0.0],
            [0.0, 1.0, 0.0, 0.0],
            [0.0, 0.0, 1.0, 0.0],
            [0.0, 0.0, 0.0, 1.0],
        ],
        "package_world_bound_m": {
            "min": minimum,
            "max": maximum,
        },
        "extent_m": [
            upper - lower
            for lower, upper in zip(minimum, maximum, strict=True)
        ],
        "identity_tolerance": 1e-6,
        "support_frame": "support",
        "support_frame_local_matrix": [
            [1.0, 0.0, 0.0, 0.0],
            [0.0, 1.0, 0.0, 0.0],
            [0.0, 0.0, 1.0, 0.0],
            [0.0, 0.0, support_z_m, 1.0],
        ],
        "support_frame_source_sha256": "3" * 64,
    }


def _rigid_source(
    source_usd: Path,
    *,
    asset_id: str,
    entry_prim: str,
    named_frames: dict[str, object],
    support_z_m: float = 0.0,
    task_qualifications: list[dict[str, object]] | None = None,
) -> LocalUSDAssetSource:
    metadata: dict[str, object] = {
        "interaction_contract": {
            "schema_version": "aan.interaction_contract.v1",
            "asset_entry_prim": entry_prim,
            "collider_prims": [
                {
                    "prim_path": f"{entry_prim}/body",
                    "collision_enabled": True,
                    "observed_approximation": "convexDecomposition",
                }
            ],
            "named_frames": named_frames,
        },
        "task_interactive_geometry": _task_geometry(
            entry_prim,
            minimum=[-0.01, -0.01, 0.0],
            maximum=[0.01, 0.01, 0.1],
            support_z_m=support_z_m,
        ),
    }
    if task_qualifications is not None:
        metadata["task_qualifications"] = task_qualifications
    return LocalUSDAssetSource(
        asset_id=asset_id,
        source_usd=source_usd,
        role="rigid_object",
        license="LicenseRef-Internal-Restricted",
        source_uri=f"convert-asset://{asset_id}/asset/sha256:" + "1" * 64,
        redistributable=False,
        root_prim_path="/World",
        upstream_package=_upstream(
            asset_id,
            metadata,
        ),
    )


def _articulated_source(source_usd: Path) -> LocalUSDAssetSource:
    root = "/World/Centrifuge"
    joints = (
        (
            "lid",
            f"{root}/group_23/RevoluteJoint",
            f"{root}/group_23",
            -1.5556521049,
            {
                "open": [-1.5556521049, -1.45],
                "closed": [-0.0872664626, 0.0],
            },
        ),
        (
            "start_button",
            f"{root}/group_2/PrismaticJoint",
            f"{root}/group_2",
            0.0,
            {
                "released": [-0.0005, 0.0],
                "pressed": [-0.0055, -0.0045],
            },
        ),
        (
            "rotor",
            f"{root}/group_6/RevoluteJoint",
            f"{root}/group_6",
            0.0,
            {"parked": [-0.05, 0.0]},
        ),
    )
    dof_mapping = [
        {"joint_prim": joint_prim, "dof_index": index}
        for index, (_, joint_prim, _, _, _) in enumerate(joints)
    ]
    closure = {
        "status": "pass",
        "articulation_roots": [{"prim_path": root}],
        "dof_mapping": dof_mapping,
        "reset_values": [
            {
                "joint_prim": joint_prim,
                "reset_value": {"status": "pass", "value": reset_value},
            }
            for _, joint_prim, _, reset_value, _ in joints
        ],
    }
    contract = {
        "schema_version": "scenario-forge-articulation-contract/v0.1",
        "asset_entry_prim": root,
        "articulation_root_prim": root,
        "runtime_units": {"revolute": "radian", "prismatic": "meter"},
        "joints": {
            semantic_name: {
                "joint_prim": joint_prim,
                "part_prim": part_prim,
                "runtime_reset_value": reset_value,
                "states": states,
            }
            for semantic_name, joint_prim, part_prim, reset_value, states in joints
        },
        "named_frames": {
            "tube_socket_0_inserted_bottom_parked_root": {
                "parent_prim": root,
                "translation_parent_local_m": [0.0, -0.02, 0.095],
                "rotation_parent_local_wxyz": [1.0, 0.0, 0.0, 0.0],
                "authoritative": True,
            }
        },
        "closure": closure,
    }
    mounting = {
        "schema_version": "aan.articulated_mounting.v1",
        "status": "pass",
        "motion_mode": "fixed_base",
        "asset_entry_prim": root,
        "coordinate_semantics": {
            "stage_up_axis": "Z",
            "linear_units": "meter",
            "quaternion_order": "wxyz",
            "support_frame": "runtime_articulation_root_pose_local",
            "mount_pose": (
                "support_plane_to_runtime_articulation_root_pose_world_axes_"
                "at_yaw_zero"
            ),
            "qualified_extents": (
                "world_axis_aligned_at_mount_pose_after_joint_reset"
            ),
        },
        "support_frame_root_local": {
            "translation_m": [0.0, -0.10363300144672394, 0.0],
            "rotation_wxyz": [1.0, 0.0, 0.0, 0.0],
        },
        "support_plane_to_root_mount_pose": {
            "translation_m": [0.0, 0.0, 0.10363300144672394],
            "rotation_wxyz": [0.5, 0.5, 0.5, 0.5],
        },
        "initial_joint_reset_positions": [
            {"dof_index": index, "position": reset_value}
            for index, (_, _, _, reset_value, _) in enumerate(joints)
        ],
        "qualified_reset_geometry": {
            "warmup_frames": 50,
            "warmup_extent_world_aabb_m": [0.3893976, 0.35, 0.4448730],
            "settle_frames": 240,
            "final_extent_world_aabb_m": [0.3893976, 0.35, 0.4448730],
        },
        "verification_required": "benchtop_stability",
        "source_sha256": "1" * 64,
        "profile_sha256": "3" * 64,
        "runtime_report_sha256": "4" * 64,
    }
    asset_id = "scientific_workbench_hci955350_centrifuge_dynamic"
    return LocalUSDAssetSource(
        asset_id=asset_id,
        source_usd=source_usd,
        role="articulated_object",
        license="LicenseRef-Internal-Restricted",
        source_uri=f"convert-asset://{asset_id}/asset/sha256:" + "1" * 64,
        redistributable=False,
        root_prim_path="/World",
        upstream_package=_upstream(
            asset_id,
            {
                "articulation_contract": contract,
                "articulation_closure": closure,
                "task_interactive_geometry": _task_geometry(
                    root,
                    minimum=[-0.1606148216, -0.174999997, 0.0],
                    maximum=[0.1606148216, 0.174999997, 0.225967365],
                )
                | {
                    "schema_version": (
                        "scenario-forge-task-interactive-geometry/v0.2"
                    ),
                    "mounting": mounting,
                    "support_frame_local_matrix": [
                        [1.0, 0.0, 0.0, 0.0],
                        [0.0, 1.0, 0.0, 0.0],
                        [0.0, 0.0, 1.0, 0.0],
                        [0.0, -0.10363300144672394, 0.0, 1.0],
                    ],
                    "support_frame_source_sha256": "4" * 64,
                },
            },
        ),
    )


def _integration_sources(tmp_path: Path) -> dict[str, LocalUSDAssetSource]:
    source_usd = tmp_path / "source" / "scene.usda"
    source_usd.parent.mkdir(parents=True)
    source_usd.write_text(
        """#usda 1.0
(
    defaultPrim = "World"
    metersPerUnit = 1
    upAxis = "Z"
)
def Xform "World"
{
    def Xform "table" {}
    def Xform "Centrifuge"
    {
        def Xform "group_2" {}
        def Xform "group_6" {}
        def Xform "group_23" {}
    }
    def Xform "TestTube" { def Xform "body" {} }
    def Xform "TubeRack" { def Xform "body" {} }
}
""",
        encoding="utf-8",
    )
    environment = LocalUSDAssetSource(
        asset_id="scientific_environment_code_room_example4_v1",
        source_usd=source_usd,
        role="environment",
        license="LicenseRef-Internal-Restricted",
        source_uri="fixture://scientific-environment",
        redistributable=False,
    )
    table = LocalUSDAssetSource(
        asset_id="scientific_workbench_ebench_table",
        source_usd=source_usd,
        role="environment",
        license="LicenseRef-Internal-Restricted",
        source_uri="fixture://scientific-workbench-table",
        redistributable=False,
    )
    rack_frames = {
        "rack_grasp": {
            "translation_body_local_usd": [0.0, -0.08, 0.07],
            "rotation_body_local_wxyz": [1.0, 0.0, 0.0, 0.0],
        },
        "socket_0_aperture": {
            "translation_body_local_usd": [0.04, 0.07, 0.09],
            "rotation_body_local_wxyz": [1.0, 0.0, 0.0, 0.0],
        },
        "socket_0_inserted_bottom": {
            "translation_body_local_usd": [0.04, 0.07, 0.055],
            "rotation_body_local_wxyz": [1.0, 0.0, 0.0, 0.0],
        },
    }
    return {
        environment.asset_id: environment,
        table.asset_id: table,
        "scientific_workbench_hci955350_centrifuge_dynamic": (
            _articulated_source(source_usd)
        ),
        "scientific_workbench_test_tube_dynamic": _rigid_source(
            source_usd,
            asset_id="scientific_workbench_test_tube_dynamic",
            entry_prim="/World/TestTube",
            named_frames={},
            support_z_m=0.005,
        ),
        "scientific_workbench_tube_rack_dynamic": _rigid_source(
            source_usd,
            asset_id="scientific_workbench_tube_rack_dynamic",
            entry_prim="/World/TubeRack",
            named_frames=rack_frames,
            support_z_m=0.0135,
            task_qualifications=[
                {
                    "qualification_id": "tube_insertion",
                    "status": "pass",
                    "report_path": "evidence/tube_insertion/report.json",
                    "report_sha256": "4" * 64,
                }
            ],
        ),
    }


def test_centrifuge_spec_uses_hci_layout_and_ordered_device_states() -> None:
    scenario = _load(generator.CENTRIFUGE_SPEC)
    objects = {item["id"]: item for item in scenario["objects"]}
    actors = {item["id"]: item for item in scenario["robot"]["actors"]}

    assert scenario["schema_version"] == "scenario-spec/v0.5"
    assert scenario["scenario_id"] == "wetlab_centrifuge_tube_load_start_no_wait"
    assert scenario["scene"] == {
        "asset_id": "scientific_environment_code_room_example4_v1",
        "root_prim_path": "/World",
        "pose": {
            "xyz": [0.2456705, -0.0069055, 0.0],
            "wxyz": [6.123233995736766e-17, 0.0, 0.0, 1.0],
            "scale_xyz": [1.0, 1.0, 1.0],
        },
    }
    assert objects["centrifuge"]["asset_id"] == (
        "scientific_workbench_hci955350_centrifuge_dynamic"
    )
    assert objects["centrifuge"]["source_prim_path"] == "/World/Centrifuge"
    assert objects["test_tube"]["source_prim_path"] == "/World/TestTube"
    assert objects["centrifuge"]["pose"]["xyz"] == [
        -0.08,
        0.0,
        generator.EBENCH_TABLETOP_Z_M + generator.TABLETOP_CLEARANCE_M,
    ]
    assert objects["test_tube"]["pose"]["xyz"] == [
        -0.25,
        0.22,
        generator.EBENCH_TABLETOP_Z_M + generator.TABLETOP_CLEARANCE_M,
    ]
    assert set(objects["centrifuge"]["named_frames"]) == {
        "tube_socket_0_inserted_bottom_parked_root"
    }
    assert actors["operating_arm"]["end_effector"] == "left"
    assert actors["auxiliary_arm"]["end_effector"] == "right"
    assert [
        (item["sequence_index"], item["type"], item["parameters"])
        for item in scenario["success"]["predicates"]
    ] == [
        (
            0,
            "relative_pose_reached",
            {
                "object": "test_tube",
                "relative_to": "centrifuge",
                "xyz_range": {
                    "x": [-0.005, 0.005],
                    "y": [0.015, 0.025],
                    "z": [0.045, 0.065],
                },
                "axis_alignment": {
                    "object_axis": "z",
                    "target_axis": "z",
                    "relative_to_part": "rotor",
                    "comparison": "<=",
                    "threshold_deg": 15.0,
                },
            },
        ),
        (
            1,
            "articulation_joint_state_reached",
            {"object": "centrifuge", "joint": "lid", "state": "closed"},
        ),
        (
            2,
            "articulation_joint_state_reached",
            {
                "object": "centrifuge",
                "joint": "start_button",
                "state": "pressed",
            },
        ),
    ]


def test_rack_insert_spec_keeps_the_two_arm_corridor_and_checks_rack_motion() -> None:
    scenario = _load(generator.RACK_INSERT_SPEC)
    objects = {item["id"]: item for item in scenario["objects"]}
    actors = {item["id"]: item for item in scenario["robot"]["actors"]}

    assert scenario["schema_version"] == "scenario-spec/v0.5"
    assert scenario["scenario_id"] == "wetlab_bimanual_hold_rack_insert_tube"
    assert scenario["scene"] == {
        "asset_id": "scientific_environment_code_room_example4_v1",
        "root_prim_path": "/World",
        "pose": {
            "xyz": [0.2456705, -0.0069055, 0.0],
            "wxyz": [6.123233995736766e-17, 0.0, 0.0, 1.0],
            "scale_xyz": [1.0, 1.0, 1.0],
        },
    }
    assert objects["tube_rack"]["source_prim_path"] == "/World/TubeRack"
    assert objects["test_tube"]["source_prim_path"] == "/World/TestTube"
    assert objects["tube_rack"]["pose"]["xyz"] == [-0.12, -0.17, 0.81]
    assert objects["test_tube"]["pose"]["xyz"] == [-0.25, 0.2, 0.81]
    assert set(objects["tube_rack"]["named_frames"]) == {
        "rack_grasp",
        "socket_0_aperture",
        "socket_0_inserted_bottom",
    }
    assert actors["stabilizing_arm"]["end_effector"] == "right"
    assert actors["inserting_arm"]["end_effector"] == "left"
    predicates = scenario["success"]["predicates"]
    assert predicates[0] == {
        "id": "tube_inserted_in_target_socket",
        "type": "relative_pose_reached",
        "sequence_index": 0,
        "parameters": {
            "object": "test_tube",
            "relative_to": "tube_rack",
            "xyz_range": {
                "x": [-0.022, -0.012],
                "y": [0.010, 0.020],
                "z": [0.060, 0.070],
            },
            "axis_alignment": {
                "object_axis": "z",
                "target_axis": "z",
                "comparison": "<=",
                "threshold_deg": 15.0,
            },
        },
    }
    assert predicates[1] == {
        "id": "rack_terminal_displacement_limited",
        "type": "object_at_initial_pose",
        "sequence_index": 1,
        "parameters": {
            "object": "tube_rack",
            "xyz_tolerance": [0.02, 0.02, 0.01],
        },
    }


def test_all_mode_compiles_and_exports_both_packages_without_runtime(
    tmp_path: Path,
    monkeypatch,
) -> None:
    bindings = tmp_path / "bindings.yaml"
    bindings.write_text("schema_version: fixture\n", encoding="utf-8")
    sources = _integration_sources(tmp_path)
    monkeypatch.setattr(
        generator,
        "resolve_scenario_source_bindings",
        lambda path: sources,
    )
    compile_calls: list[tuple[str, Path]] = []
    export_calls: list[tuple[Path, bool]] = []
    preview_calls: list[Path] = []

    def fake_compile(spec, resolved_sources, out):
        assert resolved_sources is sources
        package_root = Path(out)
        compile_calls.append((spec.scenario_id, package_root))
        return SimpleNamespace(package_root=package_root)

    def fake_export(package_root, *, legacy_v01_transport=False):
        root = Path(package_root) / "adapters/ebench/genmanip"
        export_calls.append((Path(package_root), legacy_v01_transport))
        return SimpleNamespace(output_dir=root)

    monkeypatch.setattr(generator, "compile_scenario_package", fake_compile)
    monkeypatch.setattr(generator, "export_genmanip_collected_package", fake_export)
    monkeypatch.setattr(
        generator,
        "run_genmanip_initial_preview",
        lambda collected, *args, **kwargs: preview_calls.append(Path(collected)),
    )

    output = tmp_path / "out"
    assert (
        generator.main(
            [
                "--bindings",
                str(bindings),
                "--task",
                "all",
                "--out",
                str(output),
                "--static-only",
            ]
        )
        == 0
    )

    assert compile_calls == [
        (
            "wetlab_centrifuge_tube_load_start_no_wait",
            output / "wetlab_centrifuge_tube_load_start_no_wait",
        ),
        (
            "wetlab_bimanual_hold_rack_insert_tube",
            output / "wetlab_bimanual_hold_rack_insert_tube",
        ),
    ]
    assert export_calls == [(call[1], True) for call in compile_calls]
    assert preview_calls == []


def test_materialization_uses_support_frame_and_requires_rack_insertion_gate(
    tmp_path: Path,
) -> None:
    sources = _integration_sources(tmp_path)
    raw_spec = _load(generator.RACK_INSERT_SPEC)

    materialized = generator._materialize_authoritative_task_geometry(
        "11",
        raw_spec,
        sources,
    )
    objects = {
        item["id"]: item
        for item in materialized["objects"]
        if isinstance(item, dict)
    }
    assert objects["tube_rack"]["pose"]["xyz"][2] == pytest.approx(
        generator.EBENCH_TABLETOP_Z_M
        + generator.TABLETOP_CLEARANCE_M
        - 0.0135
    )
    assert objects["test_tube"]["pose"]["xyz"][2] == pytest.approx(
        generator.EBENCH_TABLETOP_Z_M
        + generator.TABLETOP_CLEARANCE_M
        - 0.005
    )

    rack = sources["scientific_workbench_tube_rack_dynamic"]
    assert rack.upstream_package is not None
    rack.upstream_package.metadata.pop("task_qualifications")
    with pytest.raises(ValueError, match="tube_insertion"):
        generator._materialize_authoritative_task_geometry(
            "11",
            raw_spec,
            sources,
        )


def test_materialization_uses_fixed_base_mount_pose_flush_on_tabletop(
    tmp_path: Path,
) -> None:
    sources = _integration_sources(tmp_path)
    raw_spec = _load(generator.CENTRIFUGE_SPEC)

    materialized = generator._materialize_authoritative_task_geometry(
        "7",
        raw_spec,
        sources,
    )
    objects = {
        item["id"]: item
        for item in materialized["objects"]
        if isinstance(item, dict)
    }
    centrifuge_pose = objects["centrifuge"]["pose"]
    assert centrifuge_pose["xyz"] == pytest.approx(
        [
            -0.08,
            0.0,
            generator.EBENCH_TABLETOP_Z_M + 0.10363300144672394,
        ]
    )
    assert centrifuge_pose["wxyz"] == pytest.approx(
        [-0.5, -0.5, 0.5, 0.5]
    )
    assert objects["test_tube"]["pose"]["xyz"][2] == pytest.approx(
        generator.EBENCH_TABLETOP_Z_M
        + generator.TABLETOP_CLEARANCE_M
        - 0.005
    )


def test_all_mode_real_static_compile_exports_mixed_articulated_and_rigid_assets(
    tmp_path: Path,
    monkeypatch,
) -> None:
    bindings = tmp_path / "bindings.yaml"
    bindings.write_text("schema_version: fixture\n", encoding="utf-8")
    monkeypatch.setattr(
        generator,
        "resolve_scenario_source_bindings",
        lambda path: _integration_sources(tmp_path),
    )

    output = tmp_path / "out"
    assert (
        generator.main(
            [
                "--bindings",
                str(bindings),
                "--task",
                "all",
                "--out",
                str(output),
                "--static-only",
            ]
        )
        == 0
    )

    task7 = output / "wetlab_centrifuge_tube_load_start_no_wait"
    task11 = output / "wetlab_bimanual_hold_rack_insert_tube"
    task7_export = task7 / "adapters/ebench/genmanip"
    task11_export = task11 / "adapters/ebench/genmanip"
    task7_config = _load(task7_export / "tasks/config.yaml")
    task11_config = _load(task11_export / "tasks/config.yaml")
    task7_evaluation = task7_config["evaluation_configs"][0]
    task11_evaluation = task11_config["evaluation_configs"][0]

    assert task7_evaluation["object_config"]["centrifuge"]["is_articulated"] is True
    assert [
        stage[0][0]["type"]
        for stage in task7_evaluation["generation_config"]["goal"]
    ] == [
        "manip/default/sr_based_genmanip_range",
        "manip/default/sr_based_genmanip_relationship",
        "manip/default/sr_based_genmanip_relationship",
    ]
    assert [
        stage[0][0]["type"]
        for stage in task11_evaluation["generation_config"]["goal"]
    ] == [
        "manip/default/sr_based_genmanip_range",
        "manip/default/sr_based_genmanip_range",
    ]
    task7_episode = next(
        task7_export.glob(
            "tasks/scenario_forge/wetlab_centrifuge_tube_load_start_no_wait/"
            "*/episode_metadata.json"
        )
    )
    task7_data = yaml.safe_load(task7_episode.read_text(encoding="utf-8"))[
        "task_data"
    ]
    task7_layout = task7_data["initial_layout"]
    assert task7_layout["centrifuge"]["type"] == "articulation"
    assert task7_layout["centrifuge"]["position"][2] == pytest.approx(
        generator.EBENCH_TABLETOP_Z_M + 0.10363300144672394
    )
    assert task7_layout["centrifuge"]["orientation"] == pytest.approx(
        [-0.5, -0.5, 0.5, 0.5]
    )
    assert task7_layout["centrifuge"]["joint_positions"] == pytest.approx(
        [-1.5556521049, 0.0, 0.0]
    )
    assert task7_layout["test_tube"]["position"][2] == pytest.approx(
        generator.EBENCH_TABLETOP_Z_M
        + generator.TABLETOP_CLEARANCE_M
        - 0.005
    )
    assert task7_data["scenario_forge_runtime_contract"]["schema_version"] == (
        "scenario-forge-genmanip-runtime-contract/v0.1"
    )
    assert task7_data["scenario_forge_runtime_contract_v05"]["schema_version"] == (
        "scenario-forge-genmanip-runtime-contract/v0.5"
    )
    task7_contract = task7_data["scenario_forge_runtime_contract_v05"]
    task7_objects = {
        item["scenario_object_id"]: item for item in task7_contract["objects"]
    }
    assert task7_objects["centrifuge"]["named_frames"][
        "tube_socket_0_inserted_bottom_parked_root"
    ]["xyz"] == [0.0, -0.02, 0.095]
    task7_metrics = task7_evaluation["generation_config"]["goal"][0][0]
    assert task7_metrics[0]["x_range"] == [-0.1, -0.09]
    assert task7_metrics[0]["y_range"] == [-0.005, 0.005]
    assert task7_metrics[0]["z_range"] == [-0.03, -0.01]
    assert task7_metrics[1]["obj2_uid"] == "centrifuge_rotor"
    task7_request = _load(task7_export / "evidence/render_request.yaml")
    task7_expected_geometry = task7_request["expected_runtime_geometry"][
        "centrifuge"
    ]
    assert task7_expected_geometry["schema_version"] == (
        "scenario-forge-task-interactive-geometry/v0.2"
    )
    assert task7_expected_geometry["qualified_extent_m_by_sample"] == {
        "warmup_start": [0.3893976, 0.35, 0.444873],
        "post_warmup": [0.3893976, 0.35, 0.444873],
    }
    assert task7_expected_geometry["mounting"]["motion_mode"] == "fixed_base"

    task11_episode = next(
        task11_export.glob(
            "tasks/scenario_forge/wetlab_bimanual_hold_rack_insert_tube/"
            "*/episode_metadata.json"
        )
    )
    task11_data = yaml.safe_load(task11_episode.read_text(encoding="utf-8"))[
        "task_data"
    ]
    task11_layout = task11_data["initial_layout"]
    assert task11_layout["tube_rack"]["position"][2] == pytest.approx(
        generator.EBENCH_TABLETOP_Z_M
        + generator.TABLETOP_CLEARANCE_M
        - 0.0135
    )
    assert task11_layout["test_tube"]["position"][2] == pytest.approx(
        generator.EBENCH_TABLETOP_Z_M
        + generator.TABLETOP_CLEARANCE_M
        - 0.005
    )
    task11_contract = task11_data["scenario_forge_runtime_contract_v05"]
    task11_objects = {
        item["scenario_object_id"]: item for item in task11_contract["objects"]
    }
    assert task11_objects["tube_rack"]["named_frames"][
        "socket_0_aperture"
    ]["xyz"] == [0.04, 0.07, 0.09]
    assert task11_objects["tube_rack"]["named_frames"][
        "socket_0_inserted_bottom"
    ]["xyz"] == [0.04, 0.07, 0.055]
    task11_metric = task11_evaluation["generation_config"]["goal"][0][0][0]
    assert task11_metric["x_range"] == [0.035, 0.045]
    assert task11_metric["y_range"] == [0.065, 0.075]
    assert task11_metric["z_range"] == [0.05, 0.06]


@pytest.mark.skipif(
    not _DOCUMENTED_GENMANIP_CONSUMER.is_file(),
    reason="documented GenManip compatibility checkout is not available",
)
def test_generated_tasks_use_native_goals_with_documented_genmanip_consumer(
    tmp_path: Path,
    monkeypatch,
) -> None:
    bindings = tmp_path / "bindings.yaml"
    bindings.write_text("schema_version: fixture\n", encoding="utf-8")
    monkeypatch.setattr(
        generator,
        "resolve_scenario_source_bindings",
        lambda path: _integration_sources(tmp_path),
    )
    output = tmp_path / "out"

    assert (
        generator.main(
            [
                "--bindings",
                str(bindings),
                "--task",
                "all",
                "--out",
                str(output),
                "--static-only",
            ]
        )
        == 0
    )

    module_name = "_scenario_forge_documented_genmanip_consumer"
    module_spec = importlib.util.spec_from_file_location(
        module_name,
        _DOCUMENTED_GENMANIP_CONSUMER,
    )
    assert module_spec is not None and module_spec.loader is not None
    consumer = importlib.util.module_from_spec(module_spec)
    sys.modules[module_name] = consumer
    try:
        module_spec.loader.exec_module(consumer)
        for episode_path in output.glob(
            "*/adapters/ebench/genmanip/tasks/scenario_forge/*/*/"
            "episode_metadata.json"
        ):
            task_data = _load(episode_path)["task_data"]
            assert consumer.parse_runtime_contract(task_data) is None
            resolved = consumer.resolve_metric_goal(task_data, {})
            assert resolved.goal == task_data["goal"]
            assert resolved.frame_aware_metric_active is False
            assert resolved.reason == "runtime_contract_v0.1_transport_only"
    finally:
        sys.modules.pop(module_name, None)

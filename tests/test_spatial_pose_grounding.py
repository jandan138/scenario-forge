from __future__ import annotations

from pathlib import Path

import pytest

from scenario_forge.adapters.spatial_pose_grounding import (
    STANDARD_ANCHOR_CATALOG,
    CameraPoseEstimate,
    GroundedObjectPose,
    ImageBoxObservation,
    StandardAnchorSpec,
    average_multiview_object_poses,
    build_ffmpeg_keyframe_command,
    project_aabb_to_image_box,
    solve_camera_and_tabletop_poses,
)


def test_standard_anchor_catalog_and_serialization() -> None:
    kb = STANDARD_ANCHOR_CATALOG["keyboard_98key"]
    assert isinstance(kb, StandardAnchorSpec)
    assert kb.size_xyz_m == pytest.approx((0.385, 0.140, 0.038))
    laptop = STANDARD_ANCHOR_CATALOG["laptop_15_6_in"]
    assert laptop.size_xyz_m[0] == pytest.approx(0.360)

    cam = CameraPoseEstimate(
        fov_deg=54.0,
        eye_xyz=(0.02, -1.05, 1.26),
        target_xyz=(0.0, 0.08, 0.82),
        image_size_px=(1920, 1440),
        reprojection_rmse_px=1.8,
    )
    assert CameraPoseEstimate.from_mapping(cam.to_mapping()) == cam


def test_ffmpeg_keyframe_command_and_multiview_pose_averaging(tmp_path: Path) -> None:
    cmd = build_ffmpeg_keyframe_command(
        video_path=tmp_path / "walkaround.mp4",
        out_dir=tmp_path / "frames",
        fps=2.0,
        max_frames=12,
    )
    assert cmd[0] == "ffmpeg"
    assert "-i" in cmd
    assert any("fps=2" in token for token in cmd)
    assert "12" in cmd
    assert cmd[-1].endswith("frame_%04d.png")

    view_1 = [
        GroundedObjectPose(
            object_id="keyboard",
            position_xyz_m=(0.01, -0.22, 0.750),
            center_xyz_m=(0.01, -0.22, 0.769),
            size_xyz_m=(0.385, 0.140, 0.038),
            yaw_deg=2.0,
            support_parent_id="desk",
            relation_kind="rests_on",
            bbox_xyxy_px=(700.0, 900.0, 1220.0, 1060.0),
        )
    ]
    view_2 = [
        GroundedObjectPose(
            object_id="keyboard",
            position_xyz_m=(-0.01, -0.20, 0.750),
            center_xyz_m=(-0.01, -0.20, 0.769),
            size_xyz_m=(0.385, 0.140, 0.038),
            yaw_deg=-2.0,
            support_parent_id="desk",
            relation_kind="rests_on",
            bbox_xyxy_px=(705.0, 895.0, 1225.0, 1055.0),
        )
    ]
    view_3 = [
        GroundedObjectPose(
            object_id="keyboard",
            position_xyz_m=(0.00, -0.21, 0.750),
            center_xyz_m=(0.00, -0.21, 0.769),
            size_xyz_m=(0.385, 0.140, 0.038),
            yaw_deg=0.0,
            support_parent_id="desk",
            relation_kind="rests_on",
            bbox_xyxy_px=(702.0, 898.0, 1222.0, 1058.0),
        )
    ]
    # View 4 is a gross tracking outlier that should be rejected
    view_outlier = [
        GroundedObjectPose(
            object_id="keyboard",
            position_xyz_m=(1.40, 0.90, 0.750),
            center_xyz_m=(1.40, 0.90, 0.769),
            size_xyz_m=(0.385, 0.140, 0.038),
            yaw_deg=85.0,
            support_parent_id="desk",
            relation_kind="rests_on",
            bbox_xyxy_px=(100.0, 100.0, 200.0, 200.0),
        )
    ]

    fused = average_multiview_object_poses([view_1, view_2, view_3, view_outlier], outlier_sigma=2.0)
    assert len(fused) == 1
    assert fused[0].position_xyz_m == pytest.approx((0.0, -0.21, 0.750), abs=0.015)
    assert fused[0].yaw_deg == pytest.approx(0.0, abs=1.5)


def test_solve_camera_and_tabletop_poses_recovers_metric_poses_and_support_tree() -> None:
    image_size = (1920, 1440)
    desk_z = 0.750
    gt_cam = CameraPoseEstimate(
        fov_deg=55.0,
        eye_xyz=(0.02, -1.02, 1.26),
        target_xyz=(0.00, 0.06, 0.82),
        image_size_px=image_size,
    )

    # Ground-truth tabletop layout including laptop stacked_on monitor_riser
    gt_items = [
        ("keyboard", (0.00, -0.21, desk_z), (0.385, 0.140, 0.038), True),
        ("monitor_riser", (0.00, 0.12, desk_z), (0.500, 0.250, 0.128), True),
        ("laptop", (0.00, 0.12, desk_z + 0.128), (0.360, 0.245, 0.230), True),
        ("monitor_left", (-0.48, 0.14, desk_z), (0.612, 0.190, 0.365), True),
        ("sprite_bottle", (0.42, -0.06, desk_z), (0.066, 0.066, 0.225), False),
    ]

    observations: list[ImageBoxObservation] = []
    for obj_id, pos_xyz, size_xyz, is_anchor in gt_items:
        bbox = project_aabb_to_image_box(
            camera=gt_cam,
            bottom_center_xyz=pos_xyz,
            size_xyz=size_xyz,
        )
        observations.append(
            ImageBoxObservation(
                object_id=obj_id,
                bbox_xyxy_px=bbox,
                size_xyz_m=size_xyz,
                is_scale_anchor=is_anchor,
            )
        )

    result = solve_camera_and_tabletop_poses(
        image_size_px=image_size,
        observations=observations,
        desk_height_m=desk_z,
    )

    est_cam = result.camera
    assert est_cam.fov_deg == pytest.approx(gt_cam.fov_deg, abs=4.5)
    assert est_cam.eye_xyz[0] == pytest.approx(gt_cam.eye_xyz[0], abs=0.08)
    assert est_cam.eye_xyz[1] == pytest.approx(gt_cam.eye_xyz[1], abs=0.12)
    assert est_cam.eye_xyz[2] == pytest.approx(gt_cam.eye_xyz[2], abs=0.10)

    by_id = {pose.object_id: pose for pose in result.objects}
    assert set(by_id.keys()) == {item[0] for item in gt_items}

    # Check support tree: laptop stacked_on monitor_riser, others rests_on desk
    assert by_id["keyboard"].relation_kind == "rests_on"
    assert by_id["keyboard"].support_parent_id == "desk"
    assert by_id["monitor_riser"].relation_kind == "rests_on"
    assert by_id["monitor_riser"].support_parent_id == "desk"
    assert by_id["laptop"].relation_kind == "stacked_on"
    assert by_id["laptop"].support_parent_id == "monitor_riser"
    assert by_id["laptop"].position_xyz_m[2] == pytest.approx(desk_z + 0.128, abs=1e-4)

    # Check metric tabletop (x, y, z) recovery accuracy
    for obj_id, gt_pos, _, _ in gt_items:
        est_pos = by_id[obj_id].position_xyz_m
        assert est_pos[0] == pytest.approx(gt_pos[0], abs=0.06), f"{obj_id} X mismatch"
        assert est_pos[1] == pytest.approx(gt_pos[1], abs=0.08), f"{obj_id} Y mismatch"
        assert est_pos[2] == pytest.approx(gt_pos[2], abs=0.01), f"{obj_id} Z mismatch"

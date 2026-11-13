"""Pure-Python metric camera & tabletop pose grounding from 2D boxes + scale anchors.

Recovers:
- Pinhole virtual camera intrinsics/extrinsics (``fov_deg``, ``eye_xyz``, ``target_xyz``)
- Metric 3D tabletop object poses ``(x, y, z)`` on the desk and elevated risers
- Support hierarchy (``rests_on`` desk vs ``stacked_on`` carrier object)
- Deterministic ``ffmpeg`` video keyframe sampling command specs and robust
  multi-view pose fusion with outlier rejection

Never imports Blender, USD, OpenCV, or simulator SDKs.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
import math
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np
import numpy.typing as npt

FloatArray = npt.NDArray[np.float64]

SPATIAL_POSE_GROUNDING_SCHEMA_VERSION = "scenario-forge-spatial-pose-grounding/v1.0"
SUPPORT_RELATIONS = frozenset({"rests_on", "stacked_on"})


@dataclass(frozen=True)
class StandardAnchorSpec:
    anchor_id: str
    category: str
    size_xyz_m: tuple[float, float, float]
    default_elevation_above_desk_m: float = 0.0
    description: str = ""

    def to_mapping(self) -> dict[str, Any]:
        return {
            "anchor_id": self.anchor_id,
            "category": self.category,
            "size_xyz_m": [float(v) for v in self.size_xyz_m],
            "default_elevation_above_desk_m": float(self.default_elevation_above_desk_m),
            "description": self.description,
        }


STANDARD_ANCHOR_CATALOG: dict[str, StandardAnchorSpec] = {
    "keyboard_98key": StandardAnchorSpec(
        anchor_id="keyboard_98key",
        category="keyboard",
        size_xyz_m=(0.385, 0.140, 0.038),
        description="Compact 98-key mechanical desktop keyboard (385x140x38 mm)",
    ),
    "keyboard_full_104": StandardAnchorSpec(
        anchor_id="keyboard_full_104",
        category="keyboard",
        size_xyz_m=(0.440, 0.138, 0.036),
        description="Full-size 104-key desktop keyboard (440x138x36 mm)",
    ),
    "laptop_15_6_in": StandardAnchorSpec(
        anchor_id="laptop_15_6_in",
        category="laptop",
        size_xyz_m=(0.360, 0.255, 0.230),
        description="15.6-inch open clamshell notebook (width 360 mm, depth 255 mm)",
    ),
    "monitor_27_in_landscape": StandardAnchorSpec(
        anchor_id="monitor_27_in_landscape",
        category="monitor",
        size_xyz_m=(0.612, 0.190, 0.460),
        description="27-inch 16:9 desktop monitor on stand (panel width 612 mm)",
    ),
    "monitor_27_in_portrait": StandardAnchorSpec(
        anchor_id="monitor_27_in_portrait",
        category="monitor",
        size_xyz_m=(0.365, 0.190, 0.630),
        description="27-inch rotated portrait monitor on stand (panel width 365 mm)",
    ),
    "pet_bottle_500ml": StandardAnchorSpec(
        anchor_id="pet_bottle_500ml",
        category="beverage",
        size_xyz_m=(0.066, 0.066, 0.225),
        description="Standard 500 ml cylindrical PET beverage bottle (66x225 mm)",
    ),
    "a4_sheet": StandardAnchorSpec(
        anchor_id="a4_sheet",
        category="document",
        size_xyz_m=(0.210, 0.297, 0.001),
        description="ISO A4 sheet (210x297 mm)",
    ),
    "standing_desk_standard": StandardAnchorSpec(
        anchor_id="standing_desk_standard",
        category="desk",
        size_xyz_m=(1.500, 0.750, 0.750),
        description="Standard 1500x750x750 mm motorized office desk",
    ),
}


@dataclass(frozen=True)
class ImageBoxObservation:
    object_id: str
    bbox_xyxy_px: tuple[float, float, float, float]
    size_xyz_m: tuple[float, float, float]
    anchor_id: str | None = None
    is_scale_anchor: bool = False
    declared_support_id: str | None = None
    yaw_deg: float = 0.0

    @classmethod
    def from_mapping(cls, raw: Mapping[str, Any]) -> ImageBoxObservation:
        anchor_id = str(raw["anchor_id"]) if raw.get("anchor_id") else None
        raw_size = raw.get("size_xyz_m")
        if raw_size is None and anchor_id in STANDARD_ANCHOR_CATALOG:
            size_xyz = STANDARD_ANCHOR_CATALOG[anchor_id].size_xyz_m
        elif raw_size is not None:
            size_xyz = (float(raw_size[0]), float(raw_size[1]), float(raw_size[2]))
        else:
            raise ValueError(f"observation {raw.get('object_id')!r} requires size_xyz_m or valid anchor_id")
        box = raw["bbox_xyxy_px"]
        return cls(
            object_id=str(raw["object_id"]),
            bbox_xyxy_px=(float(box[0]), float(box[1]), float(box[2]), float(box[3])),
            size_xyz_m=size_xyz,
            anchor_id=anchor_id,
            is_scale_anchor=bool(raw.get("is_scale_anchor", anchor_id is not None)),
            declared_support_id=(
                str(raw["declared_support_id"])
                if raw.get("declared_support_id") is not None
                else None
            ),
            yaw_deg=float(raw.get("yaw_deg", 0.0)),
        )


@dataclass(frozen=True)
class CameraPoseEstimate:
    fov_deg: float
    eye_xyz: tuple[float, float, float]
    target_xyz: tuple[float, float, float]
    image_size_px: tuple[int, int]
    reprojection_rmse_px: float = 0.0

    def to_mapping(self) -> dict[str, Any]:
        return {
            "fov_deg": round(float(self.fov_deg), 4),
            "eye_xyz": [round(float(v), 5) for v in self.eye_xyz],
            "target_xyz": [round(float(v), 5) for v in self.target_xyz],
            "image_size_px": [int(self.image_size_px[0]), int(self.image_size_px[1])],
            "reprojection_rmse_px": round(float(self.reprojection_rmse_px), 4),
        }

    @classmethod
    def from_mapping(cls, raw: Mapping[str, Any]) -> CameraPoseEstimate:
        eye = raw["eye_xyz"]
        target = raw["target_xyz"]
        img = raw["image_size_px"]
        return cls(
            fov_deg=float(raw["fov_deg"]),
            eye_xyz=(float(eye[0]), float(eye[1]), float(eye[2])),
            target_xyz=(float(target[0]), float(target[1]), float(target[2])),
            image_size_px=(int(img[0]), int(img[1])),
            reprojection_rmse_px=float(raw.get("reprojection_rmse_px", 0.0)),
        )


@dataclass(frozen=True)
class GroundedObjectPose:
    object_id: str
    position_xyz_m: tuple[float, float, float]
    center_xyz_m: tuple[float, float, float]
    size_xyz_m: tuple[float, float, float]
    yaw_deg: float
    support_parent_id: str
    relation_kind: str
    bbox_xyxy_px: tuple[float, float, float, float]

    def to_mapping(self) -> dict[str, Any]:
        return {
            "object_id": self.object_id,
            "position_xyz_m": [round(float(v), 5) for v in self.position_xyz_m],
            "center_xyz_m": [round(float(v), 5) for v in self.center_xyz_m],
            "size_xyz_m": [round(float(v), 5) for v in self.size_xyz_m],
            "yaw_deg": round(float(self.yaw_deg), 4),
            "support_parent_id": self.support_parent_id,
            "relation_kind": self.relation_kind,
            "bbox_xyxy_px": [round(float(v), 2) for v in self.bbox_xyxy_px],
        }

    @classmethod
    def from_mapping(cls, raw: Mapping[str, Any]) -> GroundedObjectPose:
        pos = raw["position_xyz_m"]
        ctr = raw["center_xyz_m"]
        sz = raw["size_xyz_m"]
        bx = raw["bbox_xyxy_px"]
        return cls(
            object_id=str(raw["object_id"]),
            position_xyz_m=(float(pos[0]), float(pos[1]), float(pos[2])),
            center_xyz_m=(float(ctr[0]), float(ctr[1]), float(ctr[2])),
            size_xyz_m=(float(sz[0]), float(sz[1]), float(sz[2])),
            yaw_deg=float(raw.get("yaw_deg", 0.0)),
            support_parent_id=str(raw["support_parent_id"]),
            relation_kind=str(raw["relation_kind"]),
            bbox_xyxy_px=(float(bx[0]), float(bx[1]), float(bx[2]), float(bx[3])),
        )


@dataclass(frozen=True)
class SpatialPoseGroundingResult:
    camera: CameraPoseEstimate
    desk_height_m: float
    objects: tuple[GroundedObjectPose, ...]

    def to_mapping(self) -> dict[str, Any]:
        return {
            "schema_version": SPATIAL_POSE_GROUNDING_SCHEMA_VERSION,
            "desk_height_m": round(float(self.desk_height_m), 4),
            "camera": self.camera.to_mapping(),
            "objects": [obj.to_mapping() for obj in self.objects],
        }


def _camera_basis(
    eye_xyz: tuple[float, float, float],
    target_xyz: tuple[float, float, float],
) -> tuple[FloatArray, FloatArray, FloatArray, FloatArray]:
    eye = np.asarray(eye_xyz, dtype=np.float64)
    target = np.asarray(target_xyz, dtype=np.float64)
    fwd = target - eye
    norm_f = float(np.linalg.norm(fwd))
    if norm_f < 1e-8:
        raise ValueError("camera eye and target must be distinct")
    fwd /= norm_f
    world_up = np.array([0.0, 0.0, 1.0], dtype=np.float64)
    right = np.cross(fwd, world_up)
    norm_r = float(np.linalg.norm(right))
    if norm_r < 1e-6:
        right = np.array([1.0, 0.0, 0.0], dtype=np.float64)
    else:
        right /= norm_r
    up = np.cross(right, fwd)
    up /= float(np.linalg.norm(up))
    return eye, right, up, fwd


def project_aabb_to_image_box(
    *,
    camera: CameraPoseEstimate,
    bottom_center_xyz: tuple[float, float, float],
    size_xyz: tuple[float, float, float],
    yaw_deg: float = 0.0,
) -> tuple[float, float, float, float]:
    """Project an oriented 3D bounding box resting at ``bottom_center_xyz`` to pixel xyxy."""

    w_px, h_px = camera.image_size_px
    fx = (w_px / 2.0) / math.tan(math.radians(camera.fov_deg) / 2.0)
    cx, cy = w_px / 2.0, h_px / 2.0
    eye, right, up, fwd = _camera_basis(camera.eye_xyz, camera.target_xyz)

    hx, hy, hz = size_xyz[0] / 2.0, size_xyz[1] / 2.0, size_xyz[2]
    yaw_rad = math.radians(yaw_deg)
    cos_y, sin_y = math.cos(yaw_rad), math.sin(yaw_rad)
    bx, by, bz = bottom_center_xyz

    us: list[float] = []
    vs: list[float] = []
    for lx in (-hx, hx):
        for ly in (-hy, hy):
            wx = bx + cos_y * lx - sin_y * ly
            wy = by + sin_y * lx + cos_y * ly
            for wz in (bz, bz + hz):
                delta = np.array([wx, wy, wz], dtype=np.float64) - eye
                zc = float(np.dot(delta, fwd))
                zc = max(0.05, zc)
                xc = float(np.dot(delta, right))
                yc = float(np.dot(delta, up))
                us.append(cx + fx * (xc / zc))
                vs.append(cy - fx * (yc / zc))

    return (min(us), min(vs), max(us), max(vs))


def _intersect_pixel_with_plane_z(
    camera: CameraPoseEstimate,
    u_px: float,
    v_px: float,
    plane_z: float,
) -> tuple[float, float] | None:
    w_px, h_px = camera.image_size_px
    fx = (w_px / 2.0) / math.tan(math.radians(camera.fov_deg) / 2.0)
    cx, cy = w_px / 2.0, h_px / 2.0
    eye, right, up, fwd = _camera_basis(camera.eye_xyz, camera.target_xyz)

    ray = ((u_px - cx) / fx) * right + ((cy - v_px) / fx) * up + fwd
    ray /= float(np.linalg.norm(ray))
    if abs(float(ray[2])) < 1e-6:
        return None
    t = (plane_z - float(eye[2])) / float(ray[2])
    if t <= 0.05 or t > 15.0:
        return None
    pt = eye + t * ray
    return (float(pt[0]), float(pt[1]))


def _infer_support_hierarchy(
    observations: Sequence[ImageBoxObservation],
    desk_height_m: float,
) -> dict[str, tuple[str, str, float]]:
    """Return mapping object_id -> (support_parent_id, relation_kind, z_bottom_m)."""

    by_id = {obs.object_id: obs for obs in observations}
    parent_map: dict[str, str] = {}

    for obs in observations:
        if obs.declared_support_id and obs.declared_support_id in by_id:
            parent_map[obs.object_id] = obs.declared_support_id
            continue
        if obs.declared_support_id == "desk":
            parent_map[obs.object_id] = "desk"
            continue

        u0, v0, u1, v1 = obs.bbox_xyxy_px
        obs_w_px = max(1.0, u1 - u0)
        best_carrier: tuple[float, str] | None = None
        for cand in observations:
            if cand.object_id == obs.object_id:
                continue
            # Carrier must be at least as wide physically (within 2cm) and flatter/platform-like
            if obs.size_xyz_m[0] > cand.size_xyz_m[0] + 0.02:
                continue
            if cand.size_xyz_m[2] > 0.22:
                continue
            cu0, cv0, cu1, cv1 = cand.bbox_xyxy_px
            ch_px = max(1.0, cv1 - cv0)
            overlap_px = max(0.0, min(u1, cu1) - max(u0, cu0))
            horiz_frac = overlap_px / obs_w_px
            # Item's bottom v1 sits near carrier's upper surface cv0 (above carrier bottom cv1)
            vert_on_top = (cv0 - 0.20 * ch_px) <= v1 <= (cv0 + 0.58 * ch_px) and v0 < cv0
            if horiz_frac >= 0.60 and vert_on_top:
                score = horiz_frac - abs(v1 - cv0) / ch_px
                if best_carrier is None or score > best_carrier[0]:
                    best_carrier = (score, cand.object_id)
        parent_map[obs.object_id] = best_carrier[1] if best_carrier is not None else "desk"

    # Break any accidental cycle and compute cumulative elevation z_bottom
    resolved: dict[str, tuple[str, str, float]] = {}

    def _resolve(obj_id: str, visited: set[str]) -> tuple[str, str, float]:
        if obj_id in resolved:
            return resolved[obj_id]
        parent = parent_map.get(obj_id, "desk")
        if parent == "desk" or parent in visited or parent not in by_id:
            res = ("desk", "rests_on", desk_height_m)
            resolved[obj_id] = res
            return res
        _, _, parent_z = _resolve(parent, visited | {obj_id})
        res = (parent, "stacked_on", parent_z + by_id[parent].size_xyz_m[2])
        resolved[obj_id] = res
        return res

    for obs in observations:
        _resolve(obs.object_id, set())
    return resolved


def _solve_xy_for_observation(
    camera: CameraPoseEstimate,
    obs: ImageBoxObservation,
    z_bottom: float,
) -> tuple[float, float] | None:
    u0, v0, u1, v1 = obs.bbox_xyxy_px
    uc = 0.5 * (u0 + u1)
    hit = _intersect_pixel_with_plane_z(camera, uc, v1, z_bottom)
    if hit is None:
        return None
    x = hit[0]
    y = hit[1] + 0.5 * obs.size_xyz_m[1]

    # 3 Gauss-Newton steps matching projected (uc, v_bottom) to observed (uc, v1)
    eps = 1e-3
    for _ in range(3):
        b0 = project_aabb_to_image_box(
            camera=camera,
            bottom_center_xyz=(x, y, z_bottom),
            size_xyz=obs.size_xyz_m,
            yaw_deg=obs.yaw_deg,
        )
        r_u = 0.5 * (b0[0] + b0[2]) - uc
        r_v = b0[3] - v1
        if abs(r_u) + abs(r_v) < 0.05:
            break
        bx = project_aabb_to_image_box(
            camera=camera,
            bottom_center_xyz=(x + eps, y, z_bottom),
            size_xyz=obs.size_xyz_m,
            yaw_deg=obs.yaw_deg,
        )
        by = project_aabb_to_image_box(
            camera=camera,
            bottom_center_xyz=(x, y + eps, z_bottom),
            size_xyz=obs.size_xyz_m,
            yaw_deg=obs.yaw_deg,
        )
        j = np.array(
            [
                [(0.5 * (bx[0] + bx[2]) - 0.5 * (b0[0] + b0[2])) / eps, (0.5 * (by[0] + by[2]) - 0.5 * (b0[0] + b0[2])) / eps],
                [(bx[3] - b0[3]) / eps, (by[3] - b0[3]) / eps],
            ],
            dtype=np.float64,
        )
        det = float(np.linalg.det(j))
        if abs(det) < 1e-8:
            break
        step = np.linalg.solve(j, np.array([r_u, r_v], dtype=np.float64))
        x -= float(np.clip(step[0], -0.25, 0.25))
        y -= float(np.clip(step[1], -0.25, 0.25))
    return (x, y)


def solve_camera_and_tabletop_poses(
    *,
    image_size_px: tuple[int, int],
    observations: Sequence[ImageBoxObservation | Mapping[str, Any]],
    desk_height_m: float = 0.750,
    fov_deg_bounds: tuple[float, float] = (38.0, 74.0),
    initial_fov_deg: float | None = None,
) -> SpatialPoseGroundingResult:
    """Recover metric virtual camera and 3D tabletop poses + support hierarchy."""

    w_px, h_px = int(image_size_px[0]), int(image_size_px[1])
    if w_px < 16 or h_px < 16:
        raise ValueError("image_size_px must be at least 16x16")
    parsed: list[ImageBoxObservation] = [
        obs if isinstance(obs, ImageBoxObservation) else ImageBoxObservation.from_mapping(obs)
        for obs in observations
    ]
    if not parsed:
        raise ValueError("solve_camera_and_tabletop_poses requires at least one observation")

    hierarchy = _infer_support_hierarchy(parsed, desk_height_m)
    anchors = [obs for obs in parsed if obs.is_scale_anchor] or list(parsed)

    def _make_cam(params: FloatArray) -> CameraPoseEstimate:
        fov, eye_x, eye_y, eye_z, tx, ty, tz = [float(v) for v in params]
        fov = float(np.clip(fov, fov_deg_bounds[0], fov_deg_bounds[1]))
        return CameraPoseEstimate(
            fov_deg=fov,
            eye_xyz=(eye_x, eye_y, eye_z),
            target_xyz=(tx, ty, tz),
            image_size_px=(w_px, h_px),
        )

    def _residual_vec(params: FloatArray) -> FloatArray | None:
        fov, eye_x, eye_y, eye_z, tx, ty, tz = [float(v) for v in params]
        if not (fov_deg_bounds[0] <= fov <= fov_deg_bounds[1]):
            return None
        if not (
            -0.8 <= eye_x <= 0.8
            and -2.8 <= eye_y <= -0.35
            and desk_height_m + 0.12 <= eye_z <= desk_height_m + 1.45
            and -0.6 <= tx <= 0.6
            and -0.4 <= ty <= 0.6
            and desk_height_m - 0.15 <= tz <= desk_height_m + 0.45
        ):
            return None
        if eye_y >= ty - 0.25:
            return None
        cam = _make_cam(params)
        res: list[float] = []
        xs: list[float] = []
        ys: list[float] = []
        for obs in anchors:
            _, _, z_bot = hierarchy[obs.object_id]
            xy = _solve_xy_for_observation(cam, obs, z_bot)
            if xy is None:
                return None
            xs.append(xy[0])
            ys.append(xy[1])
            pred = project_aabb_to_image_box(
                camera=cam,
                bottom_center_xyz=(xy[0], xy[1], z_bot),
                size_xyz=obs.size_xyz_m,
                yaw_deg=obs.yaw_deg,
            )
            obs_b = obs.bbox_xyxy_px
            for k in range(4):
                res.append(pred[k] - obs_b[k])

        # Weak gauge prior breaking only pure (X, Y) world-origin translation ambiguity
        med_x = float(np.median(xs))
        mid_y = 0.5 * (min(ys) + max(ys))
        res.extend(
            [
                0.5 * med_x,
                0.5 * (mid_y + 0.03),
                0.2 * tx,
                0.2 * (ty - 0.06),
                0.4 * (tz - (desk_height_m + 0.07)),
            ]
        )
        return np.asarray(res, dtype=np.float64)

    fov_candidates = [initial_fov_deg] if initial_fov_deg is not None else [46.0, 54.0, 62.0]
    best_params: FloatArray | None = None
    best_cost = float("inf")

    for fov0 in fov_candidates:
        for ey0 in (-0.80, -1.05, -1.35):
            for ez0 in (desk_height_m + 0.38, desk_height_m + 0.52, desk_height_m + 0.68):
                cand = np.array(
                    [fov0, 0.0, ey0, ez0, 0.0, 0.06, desk_height_m + 0.07],
                    dtype=np.float64,
                )
                r = _residual_vec(cand)
                if r is not None:
                    cost = float(np.dot(r, r))
                    if cost < best_cost:
                        best_cost = cost
                        best_params = cand

    assert best_params is not None
    cur = best_params.copy()
    cur_r = _residual_vec(cur)
    assert cur_r is not None
    cur_cost = float(np.dot(cur_r, cur_r))

    active_dims = [1, 2, 3, 4, 5, 6] if initial_fov_deg is not None else [0, 1, 2, 3, 4, 5, 6]
    eps_vec = np.array([0.05, 1e-3, 1e-3, 1e-3, 1e-3, 1e-3, 1e-3], dtype=np.float64)
    damping = 1e-2

    for _ in range(28):
        cols: list[FloatArray] = []
        valid_jac = True
        for dim in active_dims:
            pert = cur.copy()
            pert[dim] += eps_vec[dim]
            r_pert = _residual_vec(pert)
            if r_pert is None:
                pert = cur.copy()
                pert[dim] -= eps_vec[dim]
                r_pert = _residual_vec(pert)
                if r_pert is None:
                    valid_jac = False
                    break
                cols.append((cur_r - r_pert) / eps_vec[dim])
            else:
                cols.append((r_pert - cur_r) / eps_vec[dim])
        if not valid_jac:
            break
        jac = np.column_stack(cols)
        jtj = jac.T @ jac + damping * np.eye(len(active_dims), dtype=np.float64)
        jtr = jac.T @ cur_r
        try:
            delta_sub = -np.linalg.solve(jtj, jtr)
        except np.linalg.LinAlgError:
            break
        accepted = False
        for alpha in (1.0, 0.5, 0.2, 0.05):
            trial = cur.copy()
            for idx, dim in enumerate(active_dims):
                max_step = 4.0 if dim == 0 else 0.18
                trial[dim] += float(np.clip(alpha * delta_sub[idx], -max_step, max_step))
            r_trial = _residual_vec(trial)
            if r_trial is not None:
                t_cost = float(np.dot(r_trial, r_trial))
                if t_cost < cur_cost:
                    improvement = cur_cost - t_cost
                    cur = trial
                    cur_r = r_trial
                    cur_cost = t_cost
                    damping = max(1e-5, damping * 0.5)
                    accepted = True
                    if improvement < 1e-7:
                        break
                    break
        if not accepted:
            damping *= 4.0
            if damping > 1e4:
                break

    raw_cam = _make_cam(cur)

    # Solve all objects and compute exact pixel RMSE
    prelim_xy: dict[str, tuple[float, float]] = {}
    for obs in parsed:
        _, _, z_bot = hierarchy[obs.object_id]
        xy = _solve_xy_for_observation(raw_cam, obs, z_bot)
        if xy is None:
            xy = (0.0, 0.0)
        prelim_xy[obs.object_id] = xy

    # Enforce Stacked-on horizontal clamping inside carrier footprint if needed
    by_obs = {obs.object_id: obs for obs in parsed}
    for obs in parsed:
        parent_id, rel_kind, _ = hierarchy[obs.object_id]
        if rel_kind == "stacked_on" and parent_id in prelim_xy:
            px, py = prelim_xy[parent_id]
            cx, cy = prelim_xy[obs.object_id]
            p_size = by_obs[parent_id].size_xyz_m
            max_dx = max(0.0, 0.5 * (p_size[0] - obs.size_xyz_m[0]))
            max_dy = max(0.0, 0.5 * (p_size[1] - obs.size_xyz_m[1]))
            prelim_xy[obs.object_id] = (
                float(np.clip(cx, px - max_dx, px + max_dx)),
                float(np.clip(cy, py - max_dy, py + max_dy)),
            )

    sq_px_residuals: list[float] = []
    poses: list[GroundedObjectPose] = []
    for obs in parsed:
        parent_id, rel_kind, z_bot = hierarchy[obs.object_id]
        x, y = prelim_xy[obs.object_id]
        pred_box = project_aabb_to_image_box(
            camera=raw_cam,
            bottom_center_xyz=(x, y, z_bot),
            size_xyz=obs.size_xyz_m,
            yaw_deg=obs.yaw_deg,
        )
        for k in range(4):
            sq_px_residuals.append((pred_box[k] - obs.bbox_xyxy_px[k]) ** 2)
        poses.append(
            GroundedObjectPose(
                object_id=obs.object_id,
                position_xyz_m=(x, y, z_bot),
                center_xyz_m=(x, y, z_bot + 0.5 * obs.size_xyz_m[2]),
                size_xyz_m=obs.size_xyz_m,
                yaw_deg=obs.yaw_deg,
                support_parent_id=parent_id,
                relation_kind=rel_kind,
                bbox_xyxy_px=obs.bbox_xyxy_px,
            )
        )

    rmse = math.sqrt(sum(sq_px_residuals) / max(1, len(sq_px_residuals)))
    final_cam = CameraPoseEstimate(
        fov_deg=raw_cam.fov_deg,
        eye_xyz=raw_cam.eye_xyz,
        target_xyz=raw_cam.target_xyz,
        image_size_px=raw_cam.image_size_px,
        reprojection_rmse_px=rmse,
    )
    return SpatialPoseGroundingResult(
        camera=final_cam,
        desk_height_m=desk_height_m,
        objects=tuple(poses),
    )


def build_ffmpeg_keyframe_command(
    video_path: str | Path,
    out_dir: str | Path,
    *,
    fps: float = 1.0,
    max_frames: int = 16,
    ffmpeg_bin: str = "ffmpeg",
) -> list[str]:
    """Build a deterministic ffmpeg command list for uniform keyframe extraction."""

    if fps <= 0.0 or not math.isfinite(fps):
        raise ValueError("fps must be positive")
    if max_frames < 1:
        raise ValueError("max_frames must be >= 1")
    out_pattern = Path(out_dir) / "frame_%04d.png"
    fps_str = f"{fps:g}"
    return [
        ffmpeg_bin,
        "-hide_banner",
        "-loglevel",
        "error",
        "-y",
        "-i",
        str(Path(video_path)),
        "-vf",
        f"fps={fps_str}",
        "-frames:v",
        str(int(max_frames)),
        "-q:v",
        "2",
        str(out_pattern),
    ]


def average_multiview_object_poses(
    per_view_poses: Sequence[Sequence[GroundedObjectPose]],
    *,
    outlier_sigma: float = 2.5,
) -> list[GroundedObjectPose]:
    """Fuse multi-view GroundedObjectPose estimates with MAD/sigma outlier rejection."""

    grouped: dict[str, list[GroundedObjectPose]] = {}
    order: list[str] = []
    for view in per_view_poses:
        for pose in view:
            if pose.object_id not in grouped:
                grouped[pose.object_id] = []
                order.append(pose.object_id)
            grouped[pose.object_id].append(pose)

    fused: list[GroundedObjectPose] = []
    for obj_id in order:
        samples = grouped[obj_id]
        pts = np.array([s.position_xyz_m for s in samples], dtype=np.float64)
        if len(samples) >= 3:
            med = np.median(pts, axis=0)
            dists = np.linalg.norm(pts - med, axis=1)
            mad = float(np.median(dists))
            scale = max(0.015, 1.4826 * mad)
            keep_idx = [i for i, d in enumerate(dists) if d <= outlier_sigma * scale]
            if keep_idx:
                samples = [samples[i] for i in keep_idx]
                pts = pts[keep_idx]

        mean_pos = pts.mean(axis=0)
        size_xyz = samples[0].size_xyz_m
        sin_sum = sum(math.sin(math.radians(s.yaw_deg)) for s in samples)
        cos_sum = sum(math.cos(math.radians(s.yaw_deg)) for s in samples)
        mean_yaw = math.degrees(math.atan2(sin_sum, cos_sum))

        parent_id = Counter(s.support_parent_id for s in samples).most_common(1)[0][0]
        rel_kind = Counter(s.relation_kind for s in samples).most_common(1)[0][0]

        fused.append(
            GroundedObjectPose(
                object_id=obj_id,
                position_xyz_m=(float(mean_pos[0]), float(mean_pos[1]), float(mean_pos[2])),
                center_xyz_m=(
                    float(mean_pos[0]),
                    float(mean_pos[1]),
                    float(mean_pos[2]) + 0.5 * size_xyz[2],
                ),
                size_xyz_m=size_xyz,
                yaw_deg=mean_yaw,
                support_parent_id=parent_id,
                relation_kind=rel_kind,
                bbox_xyxy_px=samples[0].bbox_xyxy_px,
            )
        )
    return fused

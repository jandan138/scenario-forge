#!/usr/bin/env python3
"""CAD-grade OpenUSD procedural geometry, vector UI/silk-screen, and single-root physics kit.

Modeled after the authoritative `IKA OVEN 125` (`Oven125`) USD architecture:
- 100% self-contained USD geometry + multi-shader `UsdPreviewSurface` PBR & emissive materials
  (zero fragile external PNG paths).
- Smooth chamfered/rounded `UsdGeom.Mesh` sheet-metal & polymer housings, lofted profiles,
  bent tubular handles, axial-fluted knurled dials, perforated grates, hex/socket screw arrays,
  and gold pogo-pin arrays.
- Razor-sharp vector 7-segment numeric displays and 5x7 micro-stroke alphanumeric silk-screen
  labels (`emissiveColor` for OLED/TFT/LED, crisp pigment for panel legends).
- Strict `ART-001` / `GEN-005` single-root fixed-base articulation (`Links/*`, `Joints/*`,
  separated `Visual` vs `Collision` scopes, positive-scale colliders only).
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import Sequence

from pxr import Gf, Sdf, Usd, UsdGeom, UsdPhysics, UsdShade


# ---------------------------------------------------------------------------
# Stage, Transforms & Quaternions
# ---------------------------------------------------------------------------

def new_cad_stage(out_path: Path, default_prim_name: str = "AssetRoot") -> Usd.Stage:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    if out_path.exists():
        out_path.unlink()
    stage = Usd.Stage.CreateNew(str(out_path))
    UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.z)
    UsdGeom.SetStageMetersPerUnit(stage, 1.0)
    UsdPhysics.SetStageKilogramsPerUnit(stage, 1.0)
    stage.SetTimeCodesPerSecond(24.0)
    stage.SetFramesPerSecond(24.0)

    root = UsdGeom.Xform.Define(stage, f"/{default_prim_name}").GetPrim()
    Usd.ModelAPI(root).SetKind("component")
    stage.SetDefaultPrim(root)
    UsdGeom.Scope.Define(stage, f"/{default_prim_name}/Materials")
    UsdGeom.Xform.Define(stage, f"/{default_prim_name}/Links")
    UsdGeom.Xform.Define(stage, f"/{default_prim_name}/Joints")
    return stage


def quat_axis_deg(axis: str, angle_deg: float) -> Gf.Quatd:
    rad = math.radians(float(angle_deg)) * 0.5
    c = math.cos(rad)
    s = math.sin(rad)
    ax = axis.upper()
    if ax == "X":
        return Gf.Quatd(c, Gf.Vec3d(s, 0.0, 0.0))
    if ax == "Y":
        return Gf.Quatd(c, Gf.Vec3d(0.0, s, 0.0))
    if ax == "Z":
        return Gf.Quatd(c, Gf.Vec3d(0.0, 0.0, s))
    raise ValueError(f"Unsupported axis: {axis}")


def quat_euler_xyz_deg(rx: float = 0.0, ry: float = 0.0, rz: float = 0.0) -> Gf.Quatd:
    qx = quat_axis_deg("X", rx)
    qy = quat_axis_deg("Y", ry)
    qz = quat_axis_deg("Z", rz)
    return qz * qy * qx


def set_xform_pose(
    prim: Usd.Prim,
    pos: Sequence[float] = (0.0, 0.0, 0.0),
    quat: Gf.Quatd | None = None,
    scale: Sequence[float] | None = None,
) -> None:
    xf = UsdGeom.Xformable(prim)
    xf.ClearXformOpOrder()
    xf.AddTranslateOp(UsdGeom.XformOp.PrecisionDouble).Set(
        Gf.Vec3d(float(pos[0]), float(pos[1]), float(pos[2]))
    )
    if quat is not None:
        xf.AddOrientOp(UsdGeom.XformOp.PrecisionDouble).Set(quat)
    if scale is not None:
        sx, sy, sz = float(scale[0]), float(scale[1]), float(scale[2])
        if sx <= 0.0 or sy <= 0.0 or sz <= 0.0:
            raise ValueError(f"Negative/zero scale forbidden on {prim.GetPath()}: {scale}")
        xf.AddScaleOp(UsdGeom.XformOp.PrecisionFloat).Set(Gf.Vec3f(sx, sy, sz))


# ---------------------------------------------------------------------------
# PBR & Emissive Material Factory
# ---------------------------------------------------------------------------

def make_pbr_material(
    stage: Usd.Stage,
    path: str,
    diffuse: tuple[float, float, float],
    *,
    metallic: float = 0.0,
    roughness: float = 0.35,
    specular: float = 0.5,
    opacity: float = 1.0,
    ior: float = 1.5,
    emissive: tuple[float, float, float] = (0.0, 0.0, 0.0),
    clearcoat: float = 0.0,
    clearcoat_roughness: float = 0.08,
) -> UsdShade.Material:
    mat = UsdShade.Material.Define(stage, path)
    sh = UsdShade.Shader.Define(stage, f"{path}/PreviewSurface")
    sh.CreateIdAttr("UsdPreviewSurface")
    sh.CreateInput("diffuseColor", Sdf.ValueTypeNames.Color3f).Set(Gf.Vec3f(*diffuse))
    sh.CreateInput("metallic", Sdf.ValueTypeNames.Float).Set(float(metallic))
    sh.CreateInput("roughness", Sdf.ValueTypeNames.Float).Set(float(roughness))
    sh.CreateInput("specularColor", Sdf.ValueTypeNames.Color3f).Set(
        Gf.Vec3f(float(specular), float(specular), float(specular))
    )
    if opacity < 0.999:
        sh.CreateInput("opacity", Sdf.ValueTypeNames.Float).Set(float(opacity))
        sh.CreateInput("ior", Sdf.ValueTypeNames.Float).Set(float(ior))
    sh.CreateInput("emissiveColor", Sdf.ValueTypeNames.Color3f).Set(Gf.Vec3f(*emissive))
    if clearcoat > 1e-4:
        sh.CreateInput("clearcoat", Sdf.ValueTypeNames.Float).Set(float(clearcoat))
        sh.CreateInput("clearcoatRoughness", Sdf.ValueTypeNames.Float).Set(
            float(clearcoat_roughness)
        )
    out = sh.CreateOutput("surface", Sdf.ValueTypeNames.Token)
    mat.CreateSurfaceOutput().ConnectToSource(out)
    return mat


def bind_mat(prim: Usd.Prim, mat: UsdShade.Material | None) -> None:
    if mat is not None:
        UsdShade.MaterialBindingAPI.Apply(prim).Bind(mat)


# ---------------------------------------------------------------------------
# Rigid Body, Articulation Joint & Positive-Scale Collider Helpers
# ---------------------------------------------------------------------------

def solid_box_inertia(mass_kg: float, dims_xyz: tuple[float, float, float]) -> tuple[float, float, float]:
    sx, sy, sz = float(dims_xyz[0]), float(dims_xyz[1]), float(dims_xyz[2])
    c = float(mass_kg) / 12.0
    return (
        max(1e-6, round(c * (sy * sy + sz * sz), 8)),
        max(1e-6, round(c * (sx * sx + sz * sz), 8)),
        max(1e-6, round(c * (sx * sx + sy * sy), 8)),
    )


def _prepend_api_schema(prim: Usd.Prim, schema_token: str) -> None:
    prim.AddAppliedSchema(schema_token)


def make_rigid_link(
    stage: Usd.Stage,
    link_path: str,
    pos: tuple[float, float, float] = (0.0, 0.0, 0.0),
    quat: Gf.Quatd | None = None,
    mass_kg: float = 1.0,
    approx_dims: tuple[float, float, float] = (0.1, 0.1, 0.1),
    com_local: tuple[float, float, float] = (0.0, 0.0, 0.0),
    *,
    disable_gravity: bool = False,
    lin_damping: float = 0.8,
    ang_damping: float = 1.2,
) -> Usd.Prim:
    xf = UsdGeom.Xform.Define(stage, link_path)
    prim = xf.GetPrim()
    set_xform_pose(prim, pos, quat or Gf.Quatd(1.0, 0.0, 0.0, 0.0))

    rb = UsdPhysics.RigidBodyAPI.Apply(prim)
    rb.CreateRigidBodyEnabledAttr(True)
    rb.CreateKinematicEnabledAttr(False)

    mass_api = UsdPhysics.MassAPI.Apply(prim)
    mass_api.CreateMassAttr(float(mass_kg))
    ix, iy, iz = solid_box_inertia(mass_kg, approx_dims)
    mass_api.CreateDiagonalInertiaAttr(Gf.Vec3f(ix, iy, iz))
    mass_api.CreateCenterOfMassAttr(Gf.Vec3f(*com_local))
    mass_api.CreatePrincipalAxesAttr(Gf.Quatf(1.0, 0.0, 0.0, 0.0))

    _prepend_api_schema(prim, "PhysxRigidBodyAPI")
    prim.CreateAttribute(
        "physxRigidBody:disableGravity", Sdf.ValueTypeNames.Bool, False
    ).Set(bool(disable_gravity))
    prim.CreateAttribute(
        "physxRigidBody:linearDamping", Sdf.ValueTypeNames.Float, False
    ).Set(float(lin_damping))
    prim.CreateAttribute(
        "physxRigidBody:angularDamping", Sdf.ValueTypeNames.Float, False
    ).Set(float(ang_damping))

    UsdGeom.Xform.Define(stage, f"{link_path}/Visual")
    col_scope = UsdGeom.Xform.Define(stage, f"{link_path}/Collision")
    col_scope.CreatePurposeAttr(UsdGeom.Tokens.guide)
    return prim


def add_base_to_world_joint(
    stage: Usd.Stage,
    joint_path: str,
    base_link_path: str,
    *,
    self_collisions: bool = False,
) -> Usd.Prim:
    fj = UsdPhysics.FixedJoint.Define(stage, joint_path)
    fj.CreateBody1Rel().SetTargets([Sdf.Path(base_link_path)])
    fj.CreateLocalPos0Attr(Gf.Vec3f(0.0, 0.0, 0.0))
    fj.CreateLocalRot0Attr(Gf.Quatf(1.0, 0.0, 0.0, 0.0))
    fj.CreateLocalPos1Attr(Gf.Vec3f(0.0, 0.0, 0.0))
    fj.CreateLocalRot1Attr(Gf.Quatf(1.0, 0.0, 0.0, 0.0))
    prim = fj.GetPrim()
    UsdPhysics.ArticulationRootAPI.Apply(prim)
    _prepend_api_schema(prim, "PhysxArticulationAPI")
    prim.CreateAttribute(
        "physxArticulation:articulationEnabled", Sdf.ValueTypeNames.Bool, False
    ).Set(True)
    prim.CreateAttribute(
        "physxArticulation:enabledSelfCollisions", Sdf.ValueTypeNames.Bool, False
    ).Set(bool(self_collisions))
    prim.CreateAttribute(
        "physxArticulation:solverPositionIterationCount", Sdf.ValueTypeNames.Int, False
    ).Set(32)
    prim.CreateAttribute(
        "physxArticulation:solverVelocityIterationCount", Sdf.ValueTypeNames.Int, False
    ).Set(16)
    return prim


def add_revolute_joint(
    stage: Usd.Stage,
    joint_path: str,
    parent_link_path: str,
    child_link_path: str,
    pivot_in_parent: tuple[float, float, float],
    axis: str,
    lower_deg: float,
    upper_deg: float,
    reset_deg: float,
    *,
    pivot_in_child: tuple[float, float, float] = (0.0, 0.0, 0.0),
    stiffness: float = 0.0,
    damping: float = 18.0,
    max_force: float = 250.0,
) -> Usd.Prim:
    rj = UsdPhysics.RevoluteJoint.Define(stage, joint_path)
    rj.CreateAxisAttr(axis.upper())
    rj.CreateLowerLimitAttr(float(lower_deg))
    rj.CreateUpperLimitAttr(float(upper_deg))
    rj.CreateBody0Rel().SetTargets([Sdf.Path(parent_link_path)])
    rj.CreateBody1Rel().SetTargets([Sdf.Path(child_link_path)])
    rj.CreateLocalPos0Attr(Gf.Vec3f(*pivot_in_parent))
    rj.CreateLocalRot0Attr(Gf.Quatf(1.0, 0.0, 0.0, 0.0))
    rj.CreateLocalPos1Attr(Gf.Vec3f(*pivot_in_child))
    rj.CreateLocalRot1Attr(Gf.Quatf(1.0, 0.0, 0.0, 0.0))
    prim = rj.GetPrim()
    drive = UsdPhysics.DriveAPI.Apply(prim, "angular")
    drive.CreateTypeAttr("force")
    drive.CreateStiffnessAttr(float(stiffness))
    drive.CreateDampingAttr(float(damping))
    drive.CreateMaxForceAttr(float(max_force))
    drive.CreateTargetPositionAttr(float(reset_deg))
    prim.CreateAttribute("state:angular:physics:position", Sdf.ValueTypeNames.Float).Set(
        float(reset_deg)
    )
    prim.CreateAttribute("state:angular:physics:velocity", Sdf.ValueTypeNames.Float).Set(0.0)
    return prim


def add_prismatic_joint(
    stage: Usd.Stage,
    joint_path: str,
    parent_link_path: str,
    child_link_path: str,
    pivot_in_parent: tuple[float, float, float],
    axis: str,
    lower_m: float,
    upper_m: float,
    reset_m: float,
    *,
    pivot_in_child: tuple[float, float, float] = (0.0, 0.0, 0.0),
    rot_in_parent: Gf.Quatf | None = None,
    rot_in_child: Gf.Quatf | None = None,
    stiffness: float = 0.0,
    damping: float = 160.0,
    max_force: float = 250.0,
) -> Usd.Prim:
    pj = UsdPhysics.PrismaticJoint.Define(stage, joint_path)
    pj.CreateAxisAttr(axis.upper())
    pj.CreateLowerLimitAttr(float(lower_m))
    pj.CreateUpperLimitAttr(float(upper_m))
    pj.CreateBody0Rel().SetTargets([Sdf.Path(parent_link_path)])
    pj.CreateBody1Rel().SetTargets([Sdf.Path(child_link_path)])
    pj.CreateLocalPos0Attr(Gf.Vec3f(*pivot_in_parent))
    pj.CreateLocalRot0Attr(rot_in_parent or Gf.Quatf(1.0, 0.0, 0.0, 0.0))
    pj.CreateLocalPos1Attr(Gf.Vec3f(*pivot_in_child))
    pj.CreateLocalRot1Attr(rot_in_child or Gf.Quatf(1.0, 0.0, 0.0, 0.0))
    prim = pj.GetPrim()
    drive = UsdPhysics.DriveAPI.Apply(prim, "linear")
    drive.CreateTypeAttr("force")
    drive.CreateStiffnessAttr(float(stiffness))
    drive.CreateDampingAttr(float(damping))
    drive.CreateMaxForceAttr(float(max_force))
    drive.CreateTargetPositionAttr(float(reset_m))
    prim.CreateAttribute("state:linear:physics:position", Sdf.ValueTypeNames.Float).Set(
        float(reset_m)
    )
    prim.CreateAttribute("state:linear:physics:velocity", Sdf.ValueTypeNames.Float).Set(0.0)
    return prim


def add_collider_box(
    stage: Usd.Stage,
    path: str,
    center: tuple[float, float, float],
    dims_xyz: tuple[float, float, float],
    quat: Gf.Quatd | None = None,
) -> Usd.Prim:
    sx, sy, sz = float(dims_xyz[0]), float(dims_xyz[1]), float(dims_xyz[2])
    if sx <= 0.0 or sy <= 0.0 or sz <= 0.0:
        raise ValueError(f"Collider dims must be strictly positive at {path}: {dims_xyz}")
    cube = UsdGeom.Cube.Define(stage, path)
    cube.CreateSizeAttr(1.0)
    cube.CreatePurposeAttr(UsdGeom.Tokens.guide)
    prim = cube.GetPrim()
    set_xform_pose(prim, center, quat, (sx, sy, sz))
    UsdPhysics.CollisionAPI.Apply(prim).CreateCollisionEnabledAttr(True)
    return prim


def add_collider_cyl(
    stage: Usd.Stage,
    path: str,
    center: tuple[float, float, float],
    radius: float,
    height: float,
    axis: str = "Z",
    quat: Gf.Quatd | None = None,
) -> Usd.Prim:
    if radius <= 0.0 or height <= 0.0:
        raise ValueError(f"Collider cylinder radius/height must be >0 at {path}")
    cyl = UsdGeom.Cylinder.Define(stage, path)
    cyl.CreateRadiusAttr(float(radius))
    cyl.CreateHeightAttr(float(height))
    cyl.CreateAxisAttr(axis.upper())
    cyl.CreatePurposeAttr(UsdGeom.Tokens.guide)
    prim = cyl.GetPrim()
    set_xform_pose(prim, center, quat)
    UsdPhysics.CollisionAPI.Apply(prim).CreateCollisionEnabledAttr(True)
    return prim


# ---------------------------------------------------------------------------
# High-Precision CAD `UsdGeom.Mesh` & Micro-Detail Generators
# ---------------------------------------------------------------------------

def _write_mesh(
    stage: Usd.Stage,
    path: str,
    points: Sequence[tuple[float, float, float]],
    faces: Sequence[Sequence[int]],
    mat: UsdShade.Material | None = None,
    pos: tuple[float, float, float] = (0.0, 0.0, 0.0),
    quat: Gf.Quatd | None = None,
) -> Usd.Prim:
    mesh = UsdGeom.Mesh.Define(stage, path)
    pts_gf = [Gf.Vec3f(float(p[0]), float(p[1]), float(p[2])) for p in points]
    counts = [len(f) for f in faces]
    indices = [int(idx) for f in faces for idx in f]

    # Compute smooth/crease-aware per-face-varying normals for crisp CAD shading
    fv_normals: list[Gf.Vec3f] = []
    for f in faces:
        if len(f) >= 3:
            p0, p1, p2 = pts_gf[f[0]], pts_gf[f[1]], pts_gf[f[2]]
            n = (p1 - p0) ^ (p2 - p0)
            length = n.GetLength()
            n_unit = (n / length) if length > 1e-12 else Gf.Vec3f(0.0, 0.0, 1.0)
        else:
            n_unit = Gf.Vec3f(0.0, 0.0, 1.0)
        for _ in f:
            fv_normals.append(n_unit)

    mesh.CreatePointsAttr(pts_gf)
    mesh.CreateFaceVertexCountsAttr(counts)
    mesh.CreateFaceVertexIndicesAttr(indices)
    mesh.CreateNormalsAttr(fv_normals)
    mesh.SetNormalsInterpolation(UsdGeom.Tokens.faceVarying)
    mesh.CreateSubdivisionSchemeAttr(UsdGeom.Tokens.none)

    if pts_gf:
        xs = [p[0] for p in pts_gf]
        ys = [p[1] for p in pts_gf]
        zs = [p[2] for p in pts_gf]
        mesh.CreateExtentAttr([Gf.Vec3f(min(xs), min(ys), min(zs)), Gf.Vec3f(max(xs), max(ys), max(zs))])

    prim = mesh.GetPrim()
    set_xform_pose(prim, pos, quat)
    bind_mat(prim, mat)
    return prim


def add_chamfered_box_mesh(
    stage: Usd.Stage,
    path: str,
    center: tuple[float, float, float],
    dims_xyz: tuple[float, float, float],
    mat: UsdShade.Material | None,
    *,
    chamfer: float = 0.0025,
    quat: Gf.Quatd | None = None,
) -> Usd.Prim:
    """24-vertex, 26-face chamfered solid block (exact sheet-metal / CNC bevel)."""
    hx, hy, hz = dims_xyz[0] * 0.5, dims_xyz[1] * 0.5, dims_xyz[2] * 0.5
    b = min(float(chamfer), hx * 0.42, hy * 0.42, hz * 0.42)
    ix, iy, iz = hx - b, hy - b, hz - b

    # 6 outer inset quads (4 verts each = 24 verts):
    # 0..3: +Z top, 4..7: -Z bottom, 8..11: +Y back, 12..15: -Y front, 16..19: +X right, 20..23: -X left
    pts = [
        # +Z (0..3) CCW seen from +Z
        (-ix, -iy, hz), (ix, -iy, hz), (ix, iy, hz), (-ix, iy, hz),
        # -Z (4..7) CCW seen from -Z
        (-ix, iy, -hz), (ix, iy, -hz), (ix, -iy, -hz), (-ix, -iy, -hz),
        # +Y (8..11) CCW seen from +Y
        (ix, hy, -iz), (-ix, hy, -iz), (-ix, hy, iz), (ix, hy, iz),
        # -Y (12..15) CCW seen from -Y
        (-ix, -hy, -iz), (ix, -hy, -iz), (ix, -hy, iz), (-ix, -hy, iz),
        # +X (16..19) CCW seen from +X
        (hx, -iy, -iz), (hx, iy, -iz), (hx, iy, iz), (hx, -iy, iz),
        # -X (20..23) CCW seen from -X
        (-hx, iy, -iz), (-hx, -iy, -iz), (-hx, -iy, iz), (-hx, iy, iz),
    ]
    faces = [
        # 6 main faces
        [0, 1, 2, 3],
        [4, 5, 6, 7],
        [8, 9, 10, 11],
        [12, 13, 14, 15],
        [16, 17, 18, 19],
        [20, 21, 22, 23],
        # 4 top edge bevels (+Z to -Y, +X, +Y, -X)
        [1, 0, 15, 14],
        [2, 1, 19, 18],
        [3, 2, 11, 10],
        [0, 3, 23, 22],
        # 4 bottom edge bevels (-Z to -Y, +X, +Y, -X)
        [13, 12, 7, 6],
        [17, 16, 6, 5],
        [9, 8, 5, 4],
        [21, 20, 4, 7],
        # 4 vertical side edge bevels
        [16, 19, 14, 13],  # +X -Y
        [8, 11, 18, 17],   # +X +Y
        [20, 23, 10, 9],   # -X +Y
        [12, 15, 22, 21],  # -X -Y
        # 8 corner triangles
        [0, 22, 15],  # -X -Y +Z
        [1, 14, 19],  # +X -Y +Z
        [2, 18, 11],  # +X +Y +Z
        [3, 10, 23],  # -X +Y +Z
        [7, 12, 21],  # -X -Y -Z
        [6, 16, 13],  # +X -Y -Z
        [5, 8, 17],   # +X +Y -Z
        [4, 20, 9],   # -X +Y -Z
    ]
    return _write_mesh(stage, path, pts, faces, mat, pos=center, quat=quat)


def add_extruded_polygon_mesh(
    stage: Usd.Stage,
    path: str,
    profile_2d: Sequence[tuple[float, float]],
    thickness: float,
    mat: UsdShade.Material | None,
    *,
    extrude_axis: str = "Z",
    pos: tuple[float, float, float] = (0.0, 0.0, 0.0),
    quat: Gf.Quatd | None = None,
) -> Usd.Prim:
    """Extrudes a 2D polygon (CCW in its plane) symmetrically in [-thickness/2, +thickness/2].

    - extrude_axis == 'Z': profile is (x, y), extruded along z
    - extrude_axis == 'X': profile is (y, z), extruded along x
    - extrude_axis == 'Y': profile is (z, x), extruded along y
    """
    n = len(profile_2d)
    if n < 3:
        raise ValueError("profile_2d needs >= 3 points")
    # Ensure CCW winding in 2D
    area2 = 0.0
    for i in range(n):
        x0, y0 = profile_2d[i]
        x1, y1 = profile_2d[(i + 1) % n]
        area2 += x0 * y1 - x1 * y0
    prof = list(profile_2d) if area2 >= 0.0 else list(reversed(profile_2d))

    h = float(thickness) * 0.5
    ax = extrude_axis.upper()

    def _to3d(u: float, v: float, w: float) -> tuple[float, float, float]:
        if ax == "Z":
            return (u, v, w)
        if ax == "X":
            return (w, u, v)
        if ax == "Y":
            return (v, w, u)
        raise ValueError(f"Invalid extrude_axis: {extrude_axis}")

    pts: list[tuple[float, float, float]] = []
    for u, v in prof:
        pts.append(_to3d(u, v, -h))
    for u, v in prof:
        pts.append(_to3d(u, v, +h))

    # Triangulate convex/ear-clipping 2D polygon so concave C-profiles & arch levers render cleanly!
    tris = _ear_clip_triangulate(prof)
    faces: list[list[int]] = []
    for a, b, c in tris:
        faces.append([c, b, a])          # -h cap
        faces.append([n + a, n + b, n + c])  # +h cap
    for i in range(n):
        j = (i + 1) % n
        faces.append([i, j, n + j, n + i])
    return _write_mesh(stage, path, pts, faces, mat, pos=pos, quat=quat)


def _ear_clip_triangulate(poly: Sequence[tuple[float, float]]) -> list[tuple[int, int, int]]:
    idxs = list(range(len(poly)))
    tris: list[tuple[int, int, int]] = []

    def _cross(o: tuple[float, float], a: tuple[float, float], b: tuple[float, float]) -> float:
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])

    def _in_tri(p: tuple[float, float], a: tuple[float, float], b: tuple[float, float], c: tuple[float, float]) -> bool:
        c1 = _cross(a, b, p)
        c2 = _cross(b, c, p)
        c3 = _cross(c, a, p)
        return c1 >= -1e-9 and c2 >= -1e-9 and c3 >= -1e-9

    guard = 0
    while len(idxs) > 3 and guard < 2000:
        guard += 1
        ear_found = False
        m = len(idxs)
        for k in range(m):
            i0 = idxs[(k - 1) % m]
            i1 = idxs[k]
            i2 = idxs[(k + 1) % m]
            a, b, c = poly[i0], poly[i1], poly[i2]
            if _cross(a, b, c) <= 1e-10:
                continue
            if any(
                j not in (i0, i1, i2) and _in_tri(poly[j], a, b, c)
                for j in idxs
            ):
                continue
            tris.append((i0, i1, i2))
            idxs.pop(k)
            ear_found = True
            break
        if not ear_found:
            break
    if len(idxs) == 3:
        tris.append((idxs[0], idxs[1], idxs[2]))
    return tris


def add_rounded_rect_prism_mesh(
    stage: Usd.Stage,
    path: str,
    center: tuple[float, float, float],
    width: float,
    depth: float,
    height: float,
    corner_r: float,
    mat: UsdShade.Material | None,
    *,
    extrude_axis: str = "Z",
    corner_segs: int = 6,
    quat: Gf.Quatd | None = None,
) -> Usd.Prim:
    """Rounded-corner vertical/horizontal prism (ideal for sleek stainless coffee nose & bezels)."""
    if extrude_axis.upper() == "Z":
        u_half, v_half, thick = width * 0.5, depth * 0.5, height
    elif extrude_axis.upper() == "Y":
        u_half, v_half, thick = height * 0.5, width * 0.5, depth
    else:
        u_half, v_half, thick = depth * 0.5, height * 0.5, width

    r = min(float(corner_r), u_half * 0.92, v_half * 0.92)
    centers = [
        (u_half - r, v_half - r, 0.0),
        (-u_half + r, v_half - r, math.pi * 0.5),
        (-u_half + r, -v_half + r, math.pi),
        (u_half - r, -v_half + r, math.pi * 1.5),
    ]
    prof: list[tuple[float, float]] = []
    for cu, cv, a0 in centers:
        for s in range(corner_segs + 1):
            ang = a0 + (math.pi * 0.5) * (s / corner_segs)
            prof.append((cu + r * math.cos(ang), cv + r * math.sin(ang)))
    return add_extruded_polygon_mesh(
        stage, path, prof, thick, mat, extrude_axis=extrude_axis, pos=center, quat=quat
    )


def add_knurled_dial_mesh(
    stage: Usd.Stage,
    path: str,
    center: tuple[float, float, float],
    radius: float,
    length: float,
    mat: UsdShade.Material | None,
    *,
    flutes: int = 36,
    flute_depth: float = 0.0008,
    axis: str = "Y",
    quat: Gf.Quatd | None = None,
) -> Usd.Prim:
    """Tactile fluted rotary encoder barrel (`Oven125` Rotor style)."""
    prof: list[tuple[float, float]] = []
    total = flutes * 2
    for i in range(total):
        ang = 2.0 * math.pi * i / total
        r = radius if (i % 2 == 0) else (radius - flute_depth)
        prof.append((r * math.cos(ang), r * math.sin(ang)))
    return add_extruded_polygon_mesh(
        stage, path, prof, length, mat, extrude_axis=axis, pos=center, quat=quat
    )


def add_lathe_mesh(
    stage: Usd.Stage,
    path: str,
    rz_profile: Sequence[tuple[float, float]],
    mat: UsdShade.Material | None,
    *,
     radial_segs: int = 32,
    pos: tuple[float, float, float] = (0.0, 0.0, 0.0),
    quat: Gf.Quatd | None = None,
) -> Usd.Prim:
    """Revolves an `(r, z)` profile around the local Z axis (cups, capsules, pogo pins, cones)."""
    pts: list[tuple[float, float, float]] = []
    rings: list[list[int]] = []
    for r, z in rz_profile:
        r_clamped = max(0.00015, float(r))
        ring: list[int] = []
        for s in range(radial_segs):
            ang = 2.0 * math.pi * s / radial_segs
            ring.append(len(pts))
            pts.append((r_clamped * math.cos(ang), r_clamped * math.sin(ang), float(z)))
        rings.append(ring)

    faces: list[list[int]] = []
    for k in range(len(rings) - 1):
        r0, r1 = rings[k], rings[k + 1]
        for s in range(radial_segs):
            sn = (s + 1) % radial_segs
            faces.append([r0[s], r0[sn], r1[sn], r1[s]])
    # Bottom and top caps if closed near axis
    if rz_profile[0][0] <= 0.002:
        c_bot = len(pts)
        pts.append((0.0, 0.0, float(rz_profile[0][1])))
        for s in range(radial_segs):
            sn = (s + 1) % radial_segs
            faces.append([c_bot, rings[0][sn], rings[0][s]])
    if rz_profile[-1][0] <= 0.002:
        c_top = len(pts)
        pts.append((0.0, 0.0, float(rz_profile[-1][1])))
        for s in range(radial_segs):
            sn = (s + 1) % radial_segs
            faces.append([c_top, rings[-1][s], rings[-1][sn]])
    return _write_mesh(stage, path, pts, faces, mat, pos=pos, quat=quat)


def add_visual_box(
    stage: Usd.Stage,
    path: str,
    center: tuple[float, float, float],
    dims_xyz: tuple[float, float, float],
    mat: UsdShade.Material | None,
    quat: Gf.Quatd | None = None,
) -> Usd.Prim:
    cube = UsdGeom.Cube.Define(stage, path)
    cube.CreateSizeAttr(1.0)
    prim = cube.GetPrim()
    set_xform_pose(prim, center, quat, dims_xyz)
    bind_mat(prim, mat)
    return prim


def add_visual_cyl(
    stage: Usd.Stage,
    path: str,
    center: tuple[float, float, float],
    radius: float,
    height: float,
    axis: str,
    mat: UsdShade.Material | None,
    quat: Gf.Quatd | None = None,
) -> Usd.Prim:
    cyl = UsdGeom.Cylinder.Define(stage, path)
    cyl.CreateRadiusAttr(float(radius))
    cyl.CreateHeightAttr(float(height))
    cyl.CreateAxisAttr(axis.upper())
    prim = cyl.GetPrim()
    set_xform_pose(prim, center, quat)
    bind_mat(prim, mat)
    return prim


def add_visual_sphere(
    stage: Usd.Stage,
    path: str,
    center: tuple[float, float, float],
    radius: float,
    mat: UsdShade.Material | None,
) -> Usd.Prim:
    sph = UsdGeom.Sphere.Define(stage, path)
    sph.CreateRadiusAttr(float(radius))
    prim = sph.GetPrim()
    set_xform_pose(prim, center)
    bind_mat(prim, mat)
    return prim


def add_socket_screw(
    stage: Usd.Stage,
    path: str,
    center: tuple[float, float, float],
    axis: str,
    mat_metal: UsdShade.Material,
    mat_dark: UsdShade.Material,
    *,
    head_r: float = 0.0028,
    head_h: float = 0.0016,
) -> None:
    UsdGeom.Xform.Define(stage, path)
    add_visual_cyl(stage, f"{path}/Head", center, head_r, head_h, axis, mat_metal)
    ax = axis.upper()
    off = head_h * 0.35
    socket_pos = (
        (center[0] + (off if ax == "X" else 0.0)),
        (center[1] + (off if ax == "Y" else 0.0)),
        (center[2] + (off if ax == "Z" else 0.0)),
    )
    add_visual_cyl(stage, f"{path}/HexSocket", socket_pos, head_r * 0.48, head_h * 0.45, axis, mat_dark)


# ---------------------------------------------------------------------------
# Vector 7-Segment & Alphanumeric Silk-Screen Micro-Geometry (`Oven125` style)
# ---------------------------------------------------------------------------

# 5x7 bitmap font for crisp vector silk-screen & OLED/LCD readouts (0..4 cols, 0..6 rows top-to-bottom)
FONT_5X7: dict[str, tuple[str, ...]] = {
    "A": ("01110", "10001", "10001", "11111", "10001", "10001", "10001"),
    "B": ("11110", "10001", "10001", "11110", "10001", "10001", "11110"),
    "C": ("01111", "10000", "10000", "10000", "10000", "10000", "01111"),
    "D": ("11110", "10001", "10001", "10001", "10001", "10001", "11110"),
    "E": ("11111", "10000", "10000", "11110", "10000", "10000", "11111"),
    "F": ("11111", "10000", "10000", "11110", "10000", "10000", "10000"),
    "G": ("01111", "10000", "10000", "10111", "10001", "10001", "01111"),
    "H": ("10001", "10001", "10001", "11111", "10001", "10001", "10001"),
    "I": ("01110", "00100", "00100", "00100", "00100", "00100", "01110"),
    "J": ("00111", "00010", "00010", "00010", "10010", "10010", "01100"),
    "K": ("10001", "10010", "10100", "11000", "10100", "10010", "10001"),
    "L": ("10000", "10000", "10000", "10000", "10000", "10000", "11111"),
    "M": ("10001", "11011", "10101", "10101", "10001", "10001", "10001"),
    "N": ("10001", "11001", "10101", "10011", "10001", "10001", "10001"),
    "O": ("01110", "10001", "10001", "10001", "10001", "10001", "01110"),
    "P": ("11110", "10001", "10001", "11110", "10000", "10000", "10000"),
    "Q": ("01110", "10001", "10001", "10001", "10101", "10010", "01101"),
    "R": ("11110", "10001", "10001", "11110", "10100", "10010", "10001"),
    "S": ("01111", "10000", "10000", "01110", "00001", "00001", "11110"),
    "T": ("11111", "00100", "00100", "00100", "00100", "00100", "00100"),
    "U": ("10001", "10001", "10001", "10001", "10001", "10001", "01110"),
    "V": ("10001", "10001", "10001", "10001", "10001", "01010", "00100"),
    "W": ("10001", "10001", "10001", "10101", "10101", "11011", "10001"),
    "X": ("10001", "10001", "01010", "00100", "01010", "10001", "10001"),
    "Y": ("10001", "10001", "01010", "00100", "00100", "00100", "00100"),
    "Z": ("11111", "00001", "00010", "00100", "01000", "10000", "11111"),
    "0": ("01110", "10011", "10101", "10101", "11001", "10001", "01110"),
    "1": ("00100", "01100", "00100", "00100", "00100", "00100", "01110"),
    "2": ("01110", "10001", "00001", "00110", "01000", "10000", "11111"),
    "3": ("11110", "00001", "00001", "01110", "00001", "00001", "11110"),
    "4": ("00010", "00110", "01010", "10010", "11111", "00010", "00010"),
    "5": ("11111", "10000", "10000", "11110", "00001", "00001", "11110"),
    "6": ("01110", "10000", "10000", "11110", "10001", "10001", "01110"),
    "7": ("11111", "00001", "00010", "00100", "01000", "01000", "01000"),
    "8": ("01110", "10001", "10001", "01110", "10001", "10001", "01110"),
    "9": ("01110", "10001", "10001", "01111", "00001", "00001", "01110"),
    "-": ("00000", "00000", "00000", "11111", "00000", "00000", "00000"),
    ".": ("00000", "00000", "00000", "00000", "00000", "00110", "00110"),
    ":": ("00000", "00110", "00110", "00000", "00110", "00110", "00000"),
    "/": ("00001", "00010", "00100", "00100", "01000", "10000", "00000"),
    "%": ("11001", "11010", "00100", "00100", "01011", "10011", "00000"),
    "+": ("00000", "00100", "00100", "11111", "00100", "00100", "00000"),
    "|": ("00100", "00100", "00100", "00100", "00100", "00100", "00100"),
    " ": ("00000", "00000", "00000", "00000", "00000", "00000", "00000"),
}


def add_panel_text_mesh(
    stage: Usd.Stage,
    path: str,
    text: str,
    mat: UsdShade.Material,
    *,
    char_height: float = 0.0045,
    relief: float = 0.0004,
    pos: tuple[float, float, float] = (0.0, 0.0, 0.0),
    quat: Gf.Quatd | None = None,
    align: str = "center",
) -> Usd.Prim:
    """Single-mesh 3D silk-screen / OLED pixel-merged text in local XY plane (+Z normal).

    Generates ONE compact `UsdGeom.Mesh` prim per text string (fast to load, razor-sharp in RTX).
    Orient with `quat` to place on vertical (-Y front) or angled control consoles!
    """
    txt = text.upper()
    px = char_height / 7.0
    char_advance = px * 6.2
    total_w = max(px, len(txt) * char_advance - px * 1.2)
    x_start = -total_w * 0.5 if align == "center" else (0.0 if align == "left" else -total_w)
    y_top = char_height * 0.5
    hz = relief * 0.5

    pts: list[tuple[float, float, float]] = []
    faces: list[list[int]] = []

    for ci, ch in enumerate(txt):
        glyph = FONT_5X7.get(ch, FONT_5X7[" "])
        cx0 = x_start + ci * char_advance
        # Merge horizontal runs per row to cut vertex count by ~60%
        for r_i, row_bits in enumerate(glyph):
            c = 0
            while c < 5:
                if row_bits[c] != "1":
                    c += 1
                    continue
                c_end = c + 1
                while c_end < 5 and row_bits[c_end] == "1":
                    c_end += 1
                x0 = cx0 + c * px
                x1 = cx0 + c_end * px - px * 0.06
                y1 = y_top - r_i * px
                y0 = y1 - px * 0.94
                b = len(pts)
                pts.extend([
                    (x0, y0, -hz), (x1, y0, -hz), (x1, y1, -hz), (x0, y1, -hz),
                    (x0, y0, +hz), (x1, y0, +hz), (x1, y1, +hz), (x0, y1, +hz),
                ])
                faces.extend([
                    [b + 4, b + 5, b + 6, b + 7],
                    [b + 0, b + 1, b + 5, b + 4],
                    [b + 1, b + 2, b + 6, b + 5],
                    [b + 2, b + 3, b + 7, b + 6],
                    [b + 3, b + 0, b + 4, b + 7],
                ])
                c = c_end
    if not pts:
        pts = [(-0.0001, -0.0001, 0.0), (0.0001, -0.0001, 0.0), (0.0, 0.0001, 0.0)]
        faces = [[0, 1, 2]]
    return _write_mesh(stage, path, pts, faces, mat, pos=pos, quat=quat)


def add_perforated_grille_mesh(
    stage: Usd.Stage,
    path: str,
    width: float,
    depth: float,
    thickness: float,
    rows: int,
    cols: int,
    slot_margin: float,
    mat: UsdShade.Material,
    *,
    pos: tuple[float, float, float] = (0.0, 0.0, 0.0),
    quat: Gf.Quatd | None = None,
) -> Usd.Prim:
    """Single-mesh laser-slotted stainless grate / louver grid in local XY plane (+Z thickness).

    Models solid longitudinal + transverse ribs leaving true physical see-through slots!
    """
    hx, hy, hz = width * 0.5, depth * 0.5, thickness * 0.5
    pts: list[tuple[float, float, float]] = []
    faces: list[list[int]] = []

    def _add_bar(x0: float, x1: float, y0: float, y1: float) -> None:
        if x1 <= x0 + 1e-6 or y1 <= y0 + 1e-6:
            return
        b = len(pts)
        pts.extend([
            (x0, y0, -hz), (x1, y0, -hz), (x1, y1, -hz), (x0, y1, -hz),
            (x0, y0, +hz), (x1, y0, +hz), (x1, y1, +hz), (x0, y1, +hz),
        ])
        faces.extend([
            [b + 4, b + 5, b + 6, b + 7],
            [b + 3, b + 2, b + 1, b + 0],
            [b + 0, b + 1, b + 5, b + 4],
            [b + 1, b + 2, b + 6, b + 5],
            [b + 2, b + 3, b + 7, b + 6],
            [b + 3, b + 0, b + 4, b + 7],
        ])

    rib = max(0.0014, float(slot_margin))
    usable_w = max(0.005, width - 2.0 * rib)
    usable_d = max(0.005, depth - 2.0 * rib)
    pitch_x = usable_w / max(1, cols)
    pitch_y = usable_d / max(1, rows)

    # Outer border + internal longitudinal & transverse bars
    for r_i in range(rows + 1):
        yc = -hy + rib * 0.5 + r_i * pitch_y if r_i < rows else hy - rib * 0.5
        _add_bar(-hx, +hx, yc - rib * 0.5, yc + rib * 0.5)
    for c_i in range(cols + 1):
        xc = -hx + rib * 0.5 + c_i * pitch_x if c_i < cols else hx - rib * 0.5
        _add_bar(xc - rib * 0.5, xc + rib * 0.5, -hy, +hy)

    return _write_mesh(stage, path, pts, faces, mat, pos=pos, quat=quat)


def measure_stage_visual_bounds(stage: Usd.Stage, root_path: str = "/AssetRoot") -> tuple[tuple[float, float, float], tuple[float, float, float]]:
    bbox_cache = UsdGeom.BBoxCache(
        Usd.TimeCode.Default(), [UsdGeom.Tokens.default_, UsdGeom.Tokens.render]
    )
    prim = stage.GetPrimAtPath(root_path)
    box = bbox_cache.ComputeWorldBound(prim).ComputeAlignedRange()
    mn, mx = box.GetMin(), box.GetMax()
    return ((float(mn[0]), float(mn[1]), float(mn[2])), (float(mx[0]), float(mx[1]), float(mx[2])))

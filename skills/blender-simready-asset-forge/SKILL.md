---
name: blender-simready-asset-forge
description: "Unified Blender 4.4+ high-craft modeling (Boolean, Bevel, SubSurf, Remesh, UV, procedural PBR, Cycles AgX 4-view studio sheets) merged with ConvertAsset & scenario-forge OpenUSD SimReady physics compilation (ART-001 Links/Joints/Collision/grasp frames & 4-engine deformable bundle/v0.2) plus mandatory independent blind critic review."
---

# Unified Blender 4.4+ → OpenUSD SimReady Asset Forge

This skill merges the repository's two historical modeling legs into one seamless, higher-capability pipeline:

1. **Blender 4.4+ Geometric & Visual Engine (`ConvertAsset/convert_asset/blender_forge/`)**:
   - Real exact **Booleans** (hollow cavities, recessed bezels, glass window frames), multi-segment **Bevels**, **Subdivision Surface** organic sculpting, **Voxel Remesh** watertight low-poly physics proxies, **Smart UV Project**, **Blender 4.4 Principled BSDF** procedural PBR, and **Cycles `AgX` + OpenImageDenoise** 4-view studio contact sheets.
2. **SimReady OpenUSD & Four-Engine Deformable Compiler (`ConvertAsset` + `scenario-forge`)**:
   - **Articulated CAD (`articulated_cad`)**: Strict `ART-001` single-root fixed-base OpenUSD (`Links/*`, `Joints/*`, `PhysicsArticulationRootAPI`, separated `Visual` vs `Collision` scopes, explicit `named_frame("grasp")`).
   - **Sculpted Deformables (`deformable_sculpted`)**: High-poly UV visual mesh + watertight remeshed physics proxy compiled directly into `multi_engine_deformable_bundle/v0.2` (Isaac / MuJoCo 4 / Newton 1.8 / Genesis + `morphtwin_spring_3dgs` sidecar).
   - **Room Environments (`room_environment`)**: Delegates to `skills/agentic-scene-factory/scripts/export_room_source_v2.py` with the same Blender 4.4+ runtime.

## Hard Runtime Requirement: Blender >= 4.4.0

- Discovery order (`resolve_blender44_bin()`): explicit `--blender-bin` → `BLENDER_BIN` env var → `G:\my_program\blender-4.4.3-windows-x64\blender.exe` / `G:\my_program\blender-4.*` / `Program Files` / `/opt/blender-4.*` → `PATH`.
- Blender `< 4.4.0` (e.g., 3.6.x) is **strictly rejected** to guarantee native `AgX` color management and 4.4 BSDF/USD parity.

## Quick Execution

```powershell
$env:PYTHONPATH = "I:\cpfs\shared\simulation\zhuzihou\dev\ConvertAsset"
& "C:\Users\Administrator\Miniconda3\envs\sim-mujoco4-py312\python.exe" -m convert_asset.blender_forge.runner `
  --pilot all `
  --cycles-device CPU
```

- **Resource safety**: Defaults to `--cycles-device CPU` at `BELOW_NORMAL_PRIORITY_CLASS` so concurrent local GPU simulation jobs remain undisturbed. Pass `--cycles-device OPTIX` only when the local GPU is idle.

## Mandatory Dual-Gate Acceptance Protocol

Every forged asset MUST pass **both** gates before admission to `scenario-forge` / `trajectory-forge` / `EOS`:

1. **Automated Geometry, Physics & Exposure Hygiene Gate (`ForgeHygieneReport`)**:
   - Measured world bounding-box error `<= 1.0 mm` against frozen `dimensions_xyz_m`;
   - `non_manifold_edge_count == 0` (watertight manifold);
   - `uv_present == True` on all visual meshes;
   - Strict `Visual` vs. `Collision` / `PhysicsProxy` separation (`proxy_triangles <= visual_triangles`);
   - All 4 Cycles `AgX` studio views pass exposure & contrast checks.
2. **Independent Blind Visual Critic Review**:
   - Invoke a fresh-context `research` subagent (blind to the authoring script internals) passing ONLY:
     - `studio_agx/studio_4view_contact_sheet.png`
     - `forge_manifest_and_critic_handoff.json` (frozen dimensions, family, hygiene stats)
   - The critic scores Silhouette/Proportions, Material/Lighting realism, Functional Affordance (cavity clearance, handle reachability, joint plausibility), and Defects (clipping, floating parts, faceting), returning an explicit `PASS` or `REVISE` verdict with concrete fix actions.


# IKA-Grade 10-Gate Acceptance (`G1..G8 + G9a + G9b`) & Visual Critic Loop

> Local amendment `2026-11-13` aligned with `docs/standards/asset-generation.md#gen-008` and
> `docs/standards/articulation.md#art-005`.

This reference defines the complete IKA-OVEN-125-grade acceptance checklist for multi-DOF
articulated hero assets, uniting deterministic physics/topology gates (`G1..G8`),
automated objective appearance checks (`G9a`), and the independent blind-review visual
critic loop (`G9b`).

## 1. Authoring Prerequisites (`scripts/cad_usd_kit.py` & `ART-005`)

1. **Explicit PhysX Applied Schemas**:
   - Every rigid link must carry `PhysxRigidBodyAPI` via `prim.AddAppliedSchema("PhysxRigidBodyAPI")`
     (in addition to `UsdPhysics.RigidBodyAPI` and `UsdPhysics.MassAPI`).
   - The fixed-base root joint (`BaseToWorld`) must carry `UsdPhysics.ArticulationRootAPI` and
     `prim.AddAppliedSchema("PhysxArticulationAPI")`.
2. **BFS Depth Joint Prim Ordering (`ART-005`)**:
   - Author `Joints/*` prims in PhysX breadth-first topological order:
     - Depth 0: `BaseToWorld`
     - Depth 1: all joints with `body0 == Links/Base`
     - Depth 2+: serial child joints (e.g. `SelectDialJoint` with `body0 == Links/DialPressCarrier`)
       placed strictly **after** all depth-1 joints so Isaac Sim DOF indices remain deterministic.
3. **CAD-Grade Geometry & UI**:
   - Use `cad_usd_kit.py` chamfered/rounded/extruded/lathed `UsdGeom.Mesh` builders for primary
     shells, lids, knobs, and drawers — never 6-face pure `UsdGeom.Cube` blocks.
   - Use `>= 3` differentiated `UsdPreviewSurface` material classes (e.g., brushed/anodized metal,
     matte polymer/elastomer, translucent glass/acrylic or emissive UI).
   - For screens/dials/silkscreen UI, either bind non-uniform file-backed `UsdUVTexture` PNGs
     (`pixel_std > 8.0`) or declare `ui_representation: vector_3d` and emit 3D vector
     silkscreen/emissive glyph meshes via `add_panel_text_mesh`.

## 2. Gate Summary (`G1..G8 + G9a + G9b`)

| Gate | Category | Pass Requirement |
| :--- | :--- | :--- |
| `G1` | `static` | `check_articulation_usd.py --mode fixed` PASS, 1 `ArticulationRootAPI`, explicit PhysX applied schemas, BFS joint prim order |
| `G2` | `reopen` | Fresh-process reopen, 0 absolute/`://` asset paths, CAD mesh/material/size floor, closed visual envelope within `<= 2.5 mm` and `Z_min = 0 +- 1 mm` |
| `G3` | `reopen` | Pairwise control AABB clearance `>= 3.0 mm`, `0` overlaps, and default `q=0` closed hood/lid does not occlude UI/screen/buttons |
| `G4` | `runtime` | Single `Articulation` discovery, `JointStateAPI` init, `120`-frame zero-action settle (`base_drift <= 0.02 mm`, `max_joint_drift <= 0.01`, no hood sag) |
| `G5` | `runtime` | Bidirectional all-DOF sweep (`>= 88%` span), spring-return micro-keys, serial composite knob press+rotate decoupling, 0 ignored `jointFriction` attrs |
| `G6` | `runtime_physics_smoke` | Direct handle/drawer world-force smoke (`physics_smoke`) meets travel threshold with fixed-base drift `<= 0.05 mm` |
| `G7` | `runtime_physics_smoke` | `600`-frame non-convex cavity/surface load-bearing (`USD-008`) with companion rigid workpieces |
| `G8` | `runtime_physics_smoke` | Loaded rail/tunnel transport under live PhysX contact (or `applicable: false` when absent) |
| `G9a` | `visual_objective` | Automated objective appearance floor: non-box primary meshes (`verts >= 10, faces >= 10, unique_normals >= 8`), `>= 3` `UsdPreviewSurface` classes, verified UI (`UsdUVTexture` PNG `pixel_std > threshold` or declared `vector_3d` meshes), valid Cycles 4-view + Isaac RTX exposure/contrast |
| `G9b` | `visual_critic` | Independent blind-review loop (`author_agent != critic_agent`), 3-pack visual inputs, all 5 dimensions `>= 8.0 / 10.0` (`<= 3` repair rounds), SHA-256 bound to source USD & reviewed PNGs |

## 3. `G9b` Blind-Review Protocol

1. **Hard Isolation**: `author_agent != critic_agent`. The critic agent never edits builders or USDs.
2. **3-Pack Visual Inputs**:
   - Manufacturer evidence (`datasheet_evidence.json`, official photos) + frozen spec (`docs/design/asset-specs/<slug>.md`).
   - 9/10 positive anchor (`external_artifacts/asset_evidence/ika-oven-125/`) & 4/10 negative anchor (`r1` flat/box renders).
   - Candidate renders (`preview_iso.png`, `preview_front.png`, `preview_detail.png`, `preview_ui.png`, `isaac_rtx_inspection.png`) covering open/closed states and UI macros.
3. **5-Dimension Rubric (`1.0–10.0`, every dimension `>= 8.0` to `PASS`)**:
   - `silhouette_and_proportion`
   - `secondary_mechanism_craft`
   - `pbr_material_hierarchy`
   - `ui_silkscreen_legibility`
   - `artifact_free_integrity`
4. **Evidence Separation (`GEN-007`)**: Passing `G1..G9b` proves `static_contract`, `reopen_and_bounds`, `physics_smoke`, and `visual` acceptance; `robot_integration` remains `NOT_TESTED_DELEGATED_TO_ASTRA`.

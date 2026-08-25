# 15 mL Small-Particle Funnel Implementation Plan

> **For agentic workers:** Execute inline in this session. Do not commit unless the user asks. Generated USD stays under `outputs/`.

**Goal:** Land a Scenario Forge dimension contract for a hollow funnel that inserts into the 15 mL tube mouth and passes ~1.2 mm GPU-PBD particles, then generate the mesh with the existing AI3DGen Blender generator.

**Architecture:** Scenario Forge owns a YAML contract plus pure-Python checks (no `pxr`, no Isaac). Mesh generation shells out to `external_artifacts/incoming/ai3dgen_share.zip`'s `glass_funnel_generator.py`. ConvertAsset later authors SDF; this plan does not reimplement collision.

**Tech Stack:** pytest, PyYAML, AI3DGen `bpy` generator, millimetre contract YAML.

## Global Constraints

- Do not import `pxr` / Isaac / `bpy` in `src/scenario_forge/{core,schemas,generation,assets,artifacts,evaluation}`.
- Do not vendor LabBuilder/SimFoundry or ConvertAsset USD conversion into Scenario Forge.
- Do not target Task 02 18 mm particles.
- 15 mL mouth inner diameter is 13.11 mm; stem outer diameter is 10.0 mm; wall 1.5 mm.
- Collision margin 0.25 mm; particle spacing 1.2 mm; `restOffset` 0.55 mm < `particleContactOffset` 0.7 mm.
- Do not commit generated meshes, USD packages, or renders.

### Task 1: Contract loader and geometric gates

**Files:**
- Create: `configs/prototypes/funnel_15ml_small_particle_v1.yaml`
- Create: `src/scenario_forge/generation/funnel_15ml_small_particle.py`
- Test: `tests/test_funnel_15ml_small_particle.py`

**Interfaces:**
- Produces: `load_funnel_15ml_small_particle_contract(path) -> dict`, `check_funnel_15ml_small_particle_contract(contract) -> dict` with keys `throat_inner_diameter_mm`, `radial_insertion_clearance_mm`, `collision_shrunk_throat_mm`, `particle_widths_in_throat`.
- Raises: `ValueError` when insertion or throat gates fail.

- [ ] **Step 1: Write failing tests** for missing loader, 15 mL insertion clearance, and throat vs 1.2 mm particles.
- [ ] **Step 2: Run tests; expect ImportError / missing attribute.**
- [ ] **Step 3: Add YAML + loader + checks.**
- [ ] **Step 4: Re-run tests; expect pass.**
- [ ] **Step 5: Write generator JSON sibling used by AI3DGen (same numbers).**

### Task 2: Generate hollow USD (out of tree)

**Files:**
- Create: `scripts/generate_funnel_15ml_small_particle.sh`
- Output: `outputs/funnel_15ml_small_particle_20260824/` (gitignored)

- [ ] **Step 1: Invoke `glass_funnel_generator.py --config ... --output-dir ... --no-render` with bpy-capable Python.**
- [ ] **Step 2: Confirm manifold shell, stem OD ≈ 10 mm, throat ID ≈ 7 mm, height ≈ 120 mm.**
- [ ] **Step 3: If bpy is unavailable, stop after Task 1 and record the exact command.**

### Task 3: ConvertAsset handoff (not in this code drop unless runtime is present)

Hand off the generated USD to `convert-asset fluid-interaction-propose --prim <funnel prim>` then qualify as `conduit` with the small-particle recipe. Scenario Forge only builds the subprocess plan already in `FluidAssetCommandPlan`.

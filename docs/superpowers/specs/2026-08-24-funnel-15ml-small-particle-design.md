# 15 mL small-particle funnel

Date: 2026-08-24

## Goal

Generate a hollow glass funnel that can (1) insert into the admitted 15 mL
centrifuge-tube mouth and (2) pass the qualified narrow-throat GPU-PBD recipe
(`scientific_workbench_small_gpu_pbd_v2`, 1.0 mm spacing). This explicitly does
**not** target Task 02's effective 18 mm exclusion scale.

## Why this shape

The 15 mL open body in
`outputs/scientific_workbench_admitted_liquid_trial_assets_20260820/.../fluid_available.usd`
has mouth inner diameter **13.11 mm**. Task 02 particles are 18 mm; they cannot
pass any stem that fits that mouth. The `fluid_available.usd` particle set is
~1.1–1.2 mm spacing. A 7 mm throat is wide enough for that recipe.

## Geometry (generator millimetres)

Keep the old archive funnel silhouette (mouth and height). Thin the stem so it
fits the 15 mL mouth with collision margin.

| Parameter | Value | Role |
|---|---|---|
| `top_diameter_mm` | 76.0 | old mouth OD |
| `frustum_height_mm` | 60.0 | cone |
| `stem_length_mm` | 60.0 | old overall height 120 mm |
| `neck_diameter_mm` | 10.0 | stem **outer** diameter |
| `wall_thickness_mm` | 1.5 | uniform shell |
| throat ID | 7.0 | `neck - 2 * wall` |
| `bevel_mm` | 0.4 | rim softening |
| `radial_segments` | 96 | watertight lathe |

Topology: closed glass solid, open lumen at inlet and outlet (AI3DGen
`glass_funnel_generator.py`). Do not vendor that generator into Scenario Forge
core layers.

## Receiver

15 mL tube mouth inner diameter: **13.11 mm** (measured on
`Tube_Body_Hollow_Mesh` at z = 101 mm). The admitted rigid package's solid
cylinder proxy is **not** a liquid cavity. Insertion and pour use a hollow SDF
tube body, as in `fluid_available.usd`.

Radial insertion clearance before collision: (13.11 − 10.0) / 2 = **1.555 mm**.
After 0.25 mm SDF margin on each body: ≈ **1.05 mm**. That is the insertion
budget. A 12 mm colleague stem only leaves 0.55 mm and is rejected.

## Liquid recipe

Do not copy `fluid_available.usd`'s contradictory
`restOffset = 5 mm` / `particleContactOffset = 1 mm`.

Qualified funnel recipe:

- particle spacing = 1.0 mm
- `particleContactOffset` = 0.7 mm
- `restOffset` = 0.55 mm (`restOffset < particleContactOffset`)
- isosurface optional for preview; not a qualification claim

Collision-shrunk throat: 7.0 − 2 × 0.35 = 6.3 mm ≈ 6.3 particle spacings.

## Collision

ConvertAsset owns SDF / partition authoring. Fast-path SDF on the visual hollow
mesh with **r10.3 as upper bounds**, offsets shrinking to ~0.25 mm. No solid
stem hull. No Scenario Forge scene-local collider patch. Funnel behavior is
`conduit`.

## Qualification claims

In-scope after ConvertAsset cold runs:

- funnel `conduit`: ≥ 90% legal-outlet delivery, zero structural leaks
- 15 mL body `reservoir` with the small recipe (separate from this funnel spec
  if the tube is not yet qualified at this particle size)

Out of scope:

- Task 02 18 mm particles
- acrylic spoon-rack insertion as a gate
- robot policy, benchmark, or episode success

## Ownership

| Piece | Owner |
|---|---|
| Dimension contract and generator JSON | Scenario Forge |
| Hollow mesh (Blender `bpy`) | AI3DGen zip, run out of tree |
| SDF / partitions / Isaac qualification | ConvertAsset |
| Generated USD / packages | `outputs/` or external artifacts, not git |

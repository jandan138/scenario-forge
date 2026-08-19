# 2026-08-18 Drying-Box Rule-Based Material Assignment POC

## Outcome

The ten procedural drying-oven assets under
`external_artifacts/incoming/drying_box/` now have textured companions:
each `usd/` directory holds `<asset>_textured.usd`, a copied `textures/`
subdirectory, and re-rendered four-view proofs (`front/left/back/right` +
`contact_sheet_textured.png`). Originals (gray clay USD + gray renders) are
untouched. All 83 semantic part names across the family are covered by
explicit rules; no part falls back to the default material.

## What was built

- `configs/material_recipes/drying_box_v1.yaml` — ordered rule table
  (part-name regex -> material) with 10 material classes: textured brushed
  stainless (ambientCG Metal009, CC0), textured light powder coat (derived
  from Metal027, CC0), and parametric chrome/zinc/plastic/rubber/button
  red/green/needle red.
- `src/scenario_forge/assets/material_recipe.py` — pure-Python recipe
  schema, validation, and first-match-wins rule matching. No USD imports
  (pure-layer boundary preserved).
- `src/scenario_forge/adapters/usd_material_assignment.py` — applies a
  recipe to a USD file via lazy `pxr`: creates `UsdPreviewSurface` materials
  under `<defaultPrim>/_materials`, copies texture files into
  `./textures/`, and returns a per-mesh assignment report.
- `scripts/apply_drying_box_materials.py` — batch driver; writes
  `_material_reports/<asset>.json` per asset.
- `scripts/build_drying_box_powdercoat_texture.py` — regenerates the
  derived powder-coat texture set (ambientCG painted-metal sets are all
  dark or distressed; the derivation re-levels Metal027's color map to
  light gray and remaps roughness into the 0.38–0.52 range).
- `external_artifacts/incoming/drying_box/_material_library/manifest.yaml` —
  texture provenance: ambientCG, CC0 1.0, sha256 of downloaded zips.

## Verification

- `tests/test_material_assignment.py`: 9 tests — recipe validation errors,
  first-match/case-insensitive/default semantics, an explicit expectation
  table for representative parts, a coverage guard asserting all 83 family
  part names match an explicit rule, and an end-to-end fixture test that
  assigns materials to a synthetic USDA and re-opens it to verify bindings,
  parametric values, texture wiring, and copied texture files.
- `python3 -m pytest -q`: 731 passed. `ruff check src tests scripts`: clean.
- Visual: textured contact sheets for all ten assets were inspected;
  enclosure/interior/control/hardware material split is readable in every
  view.

## Rendering gotchas found (affects any textured re-render)

1. **RTX PathTracing texture race**: with the default 8 render steps,
   textured surfaces can capture before async texture processing finishes
   and come out near-black (07 was the visible victim, but any asset can
   lose the race). Use enough render steps (64 verified) or warm caches.
2. **render steps advance physics**: `render-single` steps the simulation
   while rendering, so articulated parts (e.g. the 03 vacuum door on its
   damped revolute joint) visibly move across 64 steps. The four-view proofs
   were therefore rendered from physics-stripped copies (applied physics
   schemas and joint prims removed; transforms unchanged). The delivered
   `*_textured.usd` files keep their physics intact.

## Known limitations / next steps

- No nameplate/decal layer yet: brand plates, warning labels, and dial
  faces need a procedural decal generator (PIL/SVG -> alpha PNG -> offset
  card); no suitable open-source generator exists.
- The powder-coat and stainless sets are 1K and untinted per-asset;
  two-tone or per-manufacturer colorways would need either tinted texture
  variants or a MaterialX output path.
- AI whole-mesh texturing (TRELLIS.2, MIT) remains an optional adapter-side
  enhancement for baked wear; it re-meshes output, so prim structure would
  need to be preserved explicitly.

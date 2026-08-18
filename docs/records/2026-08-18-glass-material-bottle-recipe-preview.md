# Reagent-bottle OmniGlass preview on existing glassware

Date: 2026-08-18

Isaac Sim 4.1 re-rendered the four existing glass_v1 meshes with the
`manual_glassware_v1` ClearBorosilicate OmniGlass inputs overlaid in the
evidence scene. ConvertAsset `_glass_v1` packages were not rebuilt.

Explicit overlay inputs:

- `glass_color` `(0.99, 0.998, 1.0)`
- `reflection_color` `(1.0, 1.0, 1.0)`
- `frosting_roughness` `0.035`
- `glass_ior` `1.47`
- `thin_walled` `false`
- `depth` `0.002`

The flask ground joint remains unbound. The visual guide after images are
this overlay, not a new admitted package.

The published page now shows a three-step chain per vessel: pre-glass_v1 RTL,
bottle-recipe RTL, and same-camera PathTracing. The reagent bottle is the
donor reference (RTL + PathTracing, no before).

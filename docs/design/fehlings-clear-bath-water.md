# Fehling r8: clear bath water, in-bath sample color

## Decision

r7 already makes withdrawn five-layer colors readable. The remaining failure is
looking through the beaker wall and the fake bath at the immersed column: that
segment reads as a near-black empty tube. Color above the waterline is intact, so
the tube OmniGlass and sample shaders are not the primary defect.

The user required in-bath color to remain identifiable, the bath to still look
like clear water rather than a plastic block or teaching-blue volume, and the
fake-water fill (profile and 80% height) to stay unchanged. r8 is a new package
derived from frozen r7. r7 bytes are not rewritten.

## Representation

`/World/obj_beaker/VisualWater` keeps the r7 body/surface meshes, `water:profile_m`
and `water:fill_height_ratio=0.8`. No collision, mass or particle API is added.
The UsdPreviewSurface `opacity=0.12` double-sided stack is replaced with
package-local OmniGlass: near-colorless `glass_color=(0.97,0.99,1.0)`, IOR 1.333,
`thin_walled=true`, `enable_opacity=false`, `doubleSided=false`. This follows the
titration receiver's transmissive liquid path, not PreviewSurface alpha fog.

Tube, 8 mL five-layer sample, `visual_five_layers_v6` controller, contact geometry
and producer glass/physics stay r7. In-bath closeups and a through-wall camera are
acceptance views; withdrawn crops remain a non-regression check.

## Completeness and risk

Tests lock volume/profile identity, collision-free water, OmniGlass inputs and
unchanged physics/controller. Diagnostic renders compared hide-water, lowered
PreviewSurface alpha, and OmniGlass on the same r7 t3/t15/t30 cameras before
locking the recipe. PreviewSurface alpha still smoked; OmniGlass was locked.
Official r8 replay uses `maxRefractionBounces=12`. Residual grazing-angle
darkening through cylindrical beaker glass remains and is accepted on
through-wall views; in-bath closeups were the then-current color-acceptance
views. Later eye-level `front_bath` stills on frozen r8 still lost brick-red
at the round bottom; [r9](fehlings-front-bath.md) supersedes that gate.

No chemistry, heat, spill, robot or CPU/4.1 claim is added.

See [operations](../operations/fehlings-r8-clear-bath-guide.md) and
[the dated record](../records/2026-09-14-fehlings-r8-clear-bath-water.md).

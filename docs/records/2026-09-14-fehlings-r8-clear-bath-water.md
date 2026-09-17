# Fehling r8: clear bath water, in-bath sample color

## Scope and standards

User required the immersed eight-mL sample to stay nameable (blue → green →
yellow → orange → red) when looking through the beaker wall and fake bath, the
bath to still look like clear water rather than a plastic block or teaching-blue
volume, and the fake-water fill to stay unchanged. r8 is a new package derived
from frozen r7. r7 bytes are not rewritten.

Design: [clear bath water](../design/fehlings-clear-bath-water.md).
Operations: [r8 guide](../operations/fehlings-r8-clear-bath-guide.md).

规范依据：当前 MAT-001–006、STATE-001–006、VAL-001–006。规范无需新增通用规则：
嵌套透明层遮挡颜色、无碰撞假水和按物理含义分层已有正文。本次只补任务级案例：
浸入近景才是水下颜色的验收视角，不把 OmniGlass 清水配方或具体 opacity 提升为
仓库默认值。同批同步设计、操作指南、标准案例引用和交付证据。

## Source and representation

Source r7 scene SHA:
`71e38a115fc2b1e5fa8294224d16a3cc17474bc6015196e319c7d431ed460098`.

Final r8 scene SHA:
`9c883fcbe447db017df5524db0954b6292222528cfc7b9095384512c3ae2ee46`.

`/World/obj_beaker/VisualWater` keeps the r7 body/surface meshes, `water:profile_m`
and `water:fill_height_ratio=0.8`. No collision, mass or particle API is added.
UsdPreviewSurface `opacity=0.12` double-sided water is replaced with package-local
OmniGlass: `glass_color=(0.97,0.99,1.0)`, IOR 1.333, `thin_walled=true`,
`enable_opacity=false`, `doubleSided=false`. Tube, 8 mL five-layer sample,
`visual_five_layers_v6` controller and producer glass/physics remain byte-identical
to r7.

## Diagnostics

Isaac 4.5 diagnostic overlays on the frozen r7 cameras are at
`outputs/scientific_workbench_fehlings_reducing_sugar_water_bath_vr_r8_20260914/diagnostic_water_optics/`.

- Hide-water: hue above the rim is intact; the segment seen through cylindrical
  beaker glass still darkens.
- PreviewSurface opacity ~0.05, not double-sided: still smoked gray; submerged
  hue is lost. Route A is not enough.
- OmniGlass recipe: water reads as a light clear fill; blue / yellow-green /
  orange-red remain nameable underwater. Locked.

Render uses `maxRefractionBounces=12` for r8. Fill height and volume were not
changed.

## Final runtime and visual evidence

Three independent **Isaac Sim 4.5.0** runs, process IDs **374244 / 382801 /
388892**, each status `pass`, 35 checks, 38 snapshots, `glass_tube_r7=true`,
`policy_version=visual_five_layers_v6`, bound to the r8 scene SHA.

**38 final replay images** include immersed closeups, through-wall views for
immersed states, withdrawn color closeups, rack cycle and reset. Final render
manifest SHA:
`9c0453c955bb590c8336460dec523ff68294a8dd79db4505144ed402ec83edbc`.
Local implementer review: **WARN / usable**, no blocking defects; not independent
review. In-bath closeups keep nameable blue / teal-green / yellow-green /
yellow-orange / orange-red below the waterline. Grazing through-wall cameras
still darken the lower column, especially for blue/green/yellow; orange-red at
30 s remains readable. Withdrawn crops do not regress. The bath looks like a
light clear fill, not teaching-blue dye.

The 0/9/15/21/27/30 s sheet uses identical withdrawn crops, crop `(855,425,1065,850)`,
image SHA `2fd38f0c547ae9380f2706087f3ac17524212f3874a8dd6afed9047fcd1a2655`.

## Delivery

Output:
`outputs/scientific_workbench_fehlings_reducing_sugar_water_bath_vr_r8_20260914/`.
Package:
`handoff/scientific_workbench_fehlings_reducing_sugar_water_bath_vr_r8/`.
Closure: **71** package-local dependencies, no unresolved or external paths.

Canonical ZIP: **150,265,258 bytes**, SHA256
`13f4bee090ea26f83fdb37026458780baaaaf9e38915e58f19534bdaf84ada28`.
The `vr_open_tube_positive_visual_reaction` head pointed at r8 at closeout;
r7 remains the retained glass-tube source on disk and the separate CPU-r4
candidate is not reused. Later `front_bath` stills on this frozen r8 still
lost brick-red at the round bottom; [r9](2026-09-14-fehlings-r9-front-bath.md)
supersedes for in-bath viewing. r8 bytes are not rewritten. No chemistry, heat,
spill, robot or CPU/4.1 claim is added.

## Closeout checks

```bash
make check SMOKE_OUT=/tmp/scenario-forge-fehlings-r8-smoke SMOKE_SUITE_OUT=/tmp/scenario-forge-fehlings-r8-suite PHASE10X_SUITE_OUT=/tmp/scenario-forge-fehlings-r8-phase10x
```

**1028 passed, 1 skipped** in 418.21 s; Ruff, package-smoke, phase10x-smoke and
`git diff --check` all passed. This includes currently present independent worktree
tests and is not a claim that unrelated uncommitted work has been submitted.

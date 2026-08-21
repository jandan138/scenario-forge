# 2026-08-21 conical flask 90/35 glass warp admission

## Outcome

Scenario Forge admitted a **new** dynamic flask that keeps the LabUtopia
`conical_bottle03` glass look after a producer-side axisymmetric proportion
warp. The portable request is
[`../operations/scientific-workbench-conical-flask-90x35-glass-warp-admission-request.yaml`](../operations/scientific-workbench-conical-flask-90x35-glass-warp-admission-request.yaml).

This round does **not** replace
`scientific_workbench_conical_bottle03_dynamic` and does not retarget Feishu
Task 1 or Task 13.

Public identity:

- asset id `scientific_workbench_conical_flask_90x35_glass_warp`
- entry prim `/World/ConicalFlask90x35Warp`
- binding `scientific_workbench_conical_flask_90x35_glass_warp_dynamic` in
  [`../../configs/source_bindings/scientific_workbench_asset_expansion_20260810.yaml`](../../configs/source_bindings/scientific_workbench_asset_expansion_20260810.yaml)

## Why bake, not consumer scale

Uniform or constant `(k_d, k_h)` scale cannot change mouth/belly ratio. A
height-varying radial map `k_r(z)` can, but Isaac rigid/SDF bodies do not
tolerate a runtime non-uniform `xformOp:scale` on the old package. ConvertAsset
therefore baked:

```
k_h = 150 / 196.5674179
k_r(z) piecewise-linear on the identity composed Z-up mesh:
  z_belly = 0.012295 m  ->  k = 90 / 113.3053223
  z_mouth = 0.195240 m  ->  k = 35 / 49.19089655
(x, y, z) -> (k_r(z)*x, k_r(z)*y, k_h*z)
```

Root `xformOp:scale` stays `(1, 1, 1)`. Sit-ring OD lands near 68 mm; 90 mm
means **belly**, not the contact ring. `k_r` is extrapolated below the belly.

## Measured millimetres after bake (±1 mm gate)

| Quantity | Target | Measured |
|---|---|---|
| Belly OD | 90 | 90.000 mm |
| Inner mouth | 35 | 35.000 mm |
| Height / opening | 150 | 150.000 mm |

Identity facade SHA-256 remained
`82115bd942c40214fdb2bacc6f4327111b452e67280bb3405b2451ddee6a83b9`.

Producer package (ConvertAsset):

- facade SHA-256 `e312d95bc9db389382125e3b4746e9bd88a0a69bcb00e8abb52567d4d4999ed3`
- package `.../scientific_workbench_conical_flask_90x35_glass_warp_20260821/package`
- overall AAN `pass` on Isaac Sim 4.1
- interaction runtime qualification `pass`: cooked_aperture, stable_support,
  gripper proxy collision, root-motion parity
- four-view DomeLight proofs next to the package (`four_view/asset/{front,left,back,right}.png`)

Material remains `OmniSurface_Glass` (IOR 1.52, specular transmission). SDF is
preserved on the visual mesh. Open-top is required.

## Claim boundary

Proportion fit toward 90/35/150 mm only. This admission does not claim 250 mL
volume, GPU-PBD cavity, pour success, live Task 1/13 retarget, or replacement
of the identity `conical_bottle03` binding.

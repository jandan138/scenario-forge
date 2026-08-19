# Graduated cylinder round base connector glass v2 handoff

Date: 2026-08-19

## Outcome

Scenario Forge now consumes the ConvertAsset
`graduated_cylinder_250ml_glass_web_standard_v2` package through
`configs/source_bindings/scientific_workbench_glass_web_standard_v2_20260819.yaml`.
The aggregate v2 handoff reuses the other five admitted packages and replaces
only the graduated-cylinder v1 package.

The fixed-camera Isaac Sim 4.1 comparison is under
`outputs/scientific_workbench_glass_web_standard_v2_20260819/evidence/connector_comparison/`.
The v1 image shows the cyan translucent-PP round connector. The v2 image removes
that band and makes the connector visually consistent with the thick clear-glass
base. It appears dark against the navy worktop because of reflection and
refraction; composed USD inspection confirms it is not an opaque black fallback.

## Delivery

The independent archive is:

`outputs/scientific_workbench_glass_web_standard_v2_20260819/handoff/scientific_workbench_glass_web_standard_v2.zip`

SHA-256:

`e4a359ac865763ceddda35694db45d256daa48c40245134b6ff997541e77325c`

The public guide and provenance now identify the cylinder connector fix as
`glass_web_standard_v2`. Existing task packages remain unchanged and must opt in
to this asset revision explicitly. No robot-policy, liquid-transfer, or
benchmark claim is added.

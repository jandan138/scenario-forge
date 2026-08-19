# 2026-08-20 Liquid autofill tool

Added the `scenario-forge liquid inspect/add` product surface and a strict
`aan.gpu_pbd_autofill_result.v1` consumer. Delivery uses ConvertAsset's dependency closure, a
relative alias USD, deterministic ZIP timestamps/checksums, and a final eight-second full-scene
integration observation.

The implementation is pinned to the Task 02 r10.3 effective liquid recipe rather than a newly
tuned approximation. Real regression uses the production quantity-cylinder and beaker geometry.
Failures retain diagnostics and cannot leave a formal-looking package.

Claim boundary: initial liquid only. No robot, pouring, metric, or benchmark result is inferred.

## Golden regression

The Task 02 r10.3 quantity-cylinder regression passed three producer cold starts plus the final
self-contained scene integration in EOS-managed Isaac Sim 4.1. All four eight-second runs retained
198/198 live particles, observed zero particles below the recovered cavity floor, and measured a
settled q95 fill ratio between 0.191 and 0.192 for a 0.20 target. The packaged stage opened with
`/World` as its default prim and the ZIP integrity check passed.

## Tutorial browser QA

The `/liquid-autofill/` tutorial was audited in Chromium at 1440×1000, 900×1100, and 390×844.
The first pass found horizontal overflow from command-block minimum widths at tablet and mobile
sizes. After constraining the two-column grid and long inline code, the final pass had no page or
console errors, failed requests, broken links, raw LaTeX, document overflow, or out-of-viewport
elements. Temporary screenshots and the audit JSON are under
`/tmp/scenario-forge-liquid-autofill-browser-audit-20260820/`.

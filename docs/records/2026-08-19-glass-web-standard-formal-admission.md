# Glass webpage standard formal admission

Date: 2026-08-19

## Outcome

The public `glass-material-guide` visual setup is now the formal admission
baseline instead of a preview. Scenario Forge consumes six immutable
ConvertAsset packages through
`configs/source_bindings/scientific_workbench_glass_web_standard_20260819.yaml`.

The four pre-existing vessels reproduce the complete webpage material state.
The reagent bottle and Erlenmeyer flask preserve the producer's original
SimReady materials. Scenario Forge does not recreate the USD/MDL conversion.

## Visual gate

`scripts/ebench/render_scientific_workbench_glass_web_standard.py` renders the
reference and admitted package with the same modern wet-chemistry room,
2000x800x755 mm table, camera, lighting, pose, renderer, and resolution. The
results and review live under:

`outputs/scientific_workbench_glass_web_standard_20260819/evidence/comparisons/`

The visual review passed all six candidates. In particular:

- the graduated cylinder remains transparent in thick-wall mode and includes
  the requested glass hexagonal base;
- the reagent-bottle neck remains transparent and matches the producer
  SimReady reference; and
- the Erlenmeyer clear body, red 29/42 marking, white volume marking, and
  original material partition remain visible.

The review was performed locally because this environment has no browser or
Playwright installation and delegated review was not authorized. The USD
render inspection is complete; the updated static page has source, asset,
hash, responsive, and accessibility regression coverage but no automated real
browser screenshot in this run.

## Handoff

The independent package archive is:

`outputs/scientific_workbench_glass_web_standard_20260819/handoff/scientific_workbench_glass_web_standard.zip`

SHA-256:
`663671ab36c33c89cf1bcd12481c957922d4237b9386f0672f095f7aeb2cfa36`.

The archive uses `scenario-forge-asset-handoff/v0.2`, which records either
`visual_material_override` or `original_material_visual_preservation` per
asset. It contains no task revision and makes no robot-policy, liquid-transfer,
physical-calibration, or benchmark-success claim.

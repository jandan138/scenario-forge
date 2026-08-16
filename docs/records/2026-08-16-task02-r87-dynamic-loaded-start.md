# Task 02 r8.7 dynamic-loaded-start package

Date: 2026-08-16

## Outcome

Scenario Forge generated Task 02 r8.7 by strictly consuming ConvertAsset's
promoted `dynamic_loaded_start` package. The compiler no longer applies the
historical consumer-side `-7 mm` correction: it maps the measured
support-relative entry-root pose to the intended tabletop anchor and transforms
the producer's 580 source-root-local particles with the same pose.

```text
outputs/scientific_workbench_task02_r87_20260816/ebench/
```

The package passed the native GenManip initial-scene preview and an eight-second,
960-step Isaac Sim 4.1 product smoke. Reviewed overview, workspace, and object
closeups show the cylinder upright on the table with the blue liquid contained
and no external initial clump.

## Contract changes

- `scenario_forge.adapters.convert_asset` validates the producer contract,
  report, local particle state, hashes, cold-run count, and thresholds.
- `scripts/generate_scientific_workbench_task02_r8.py` emits r8.7 by default
  while keeping r8.5/r8.6 artifacts intact.
- No simulator SDK entered a pure package layer and no ConvertAsset conversion
  or physics repair was reimplemented.

EOS verified the main r8.7 objective in the first frozen formal attempt: over
766 consecutive warmup/grasp/lift samples, maximum particles outside the source
was zero. The separate three-of-three full robot gate is still blocked by
cylinder pose instability during tilt/return; r8.7 must not be described as
3/3 robot-task success.

## Publication and CI closure

The public task directory now selects r8.7 by default and retains r8.3 in the
expandable package history. Its published overview is byte-identical to the
reviewed r8.7 `scene_overview.png`. Desktop, tablet, and mobile Chromium checks
cover image loading, version switching, console/request errors, horizontal
overflow, and long package-name wrapping.

Task 02 unit tests now create their preview request under `tmp_path`; they no
longer read the ignored local `outputs/` tree. This makes the repository check
representative of a clean GitHub Actions checkout without committing generated
scenario packages.

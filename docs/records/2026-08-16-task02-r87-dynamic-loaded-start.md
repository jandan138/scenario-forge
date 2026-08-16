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

EOS first verified the loaded-start objective over 766 consecutive
warmup/grasp/lift samples with zero particles outside the source. It then fixed
the downstream robot-control instability without changing the package,
GenManip, vessel physics, or liquid parameters. The frozen scripted-oracle
protocol passed three of three fresh Isaac Sim 4.1 cold starts: 570, 560, and
569 of 580 particles reached the target beaker, with zero spill and zero
below-support particles in every run. This is scripted robot-oracle evidence;
it is not learned-policy success, an active liquid metric, a benchmark result,
or real-liquid calibration.

The public, reader-oriented explanation is the
[graduated-cylinder GPU-PBD liquid tutorial](../liquid-cylinder-tutorial/).

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

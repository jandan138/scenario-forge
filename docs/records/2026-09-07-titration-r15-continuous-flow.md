# Titration VR r1.5: continuous flow and a wider endpoint window

## Agreed behavior

The scene retains r1.4 hardware, contact geometry, materials, internal visual
liquid and the 20 × 5 mm stir bar. Scenario Forge replaces only the task's
embedded flow/color/success policy. The promoted ConvertAsset dependencies are
retained byte-for-byte; their original evidence qualifies the producer asset,
while fresh scene evidence qualifies this task policy.

The measured joint angle is made absolute and clamped to 0–90 degrees. At or
below 5 degrees flow is zero; above it, flow in mL/s is
`(30/11) * (angle - 5) / 85`. Initial capacity remains 25 mL. Elapsed simulation
time, including steps longer than 0.1 s, advances volume; wall-clock waiting and
paused simulation do not. Transfer is capped by remaining burette volume.

Color follows cumulative receiver volume:

- Below `150/11` mL: colorless.
- From `150/11` to 15 mL: linear color interpolation to pale pink.
- From 15 through `3165/187` mL inclusive: stable pale pink and valid endpoint.
- Above `3165/187` mL: overshoot; the next 1 mL interpolates to the existing
  deep-pink color.

A constant 90-degree setting starts the transition at 5 simulation seconds,
reaches pale pink at 5.5 s, and has a 12/17 s pale interval. At 45 degrees those
values are 10.625 s, 11.6875 s, and 1.5 s. At 25 degrees the pale interval is
3 s; at 10 degrees it is 12 s. Changing angle consumes the same remaining
volume window; it does not restart a timer. Closing freezes volume and color.

## Success and compatibility

There is no required coarse/fine/drip sequence. While the receiver is within
the stable pale interval, closing to at most 5 degrees for 3 consecutive
simulation seconds completes the task. Reopening before completion resets
the hold counter. Overshooting before success prevents success until reset.

Completion latches until reset. Later operation still changes the visual
state and current volume, but never revokes success. The new double attributes
`titration:completion_volume_ml` and `titration:completion_hold_seconds` preserve
completion evidence separately from live values. Their reset defaults are
-1 mL and 0 s. `titration:policy_version` is `linear_deadzone_v1`.

Existing prim paths, legacy valve-state labels and visit flags remain available;
the labels and visit flags are diagnostic only. `valve_open_fraction` now
reports effective opening after the dead zone. Task YAML and VR configuration
publish the same `flow_curve`, transition and success-window parameters.
Coarse/fine score entries and ordered-sequence gates are removed. Remaining
metric weights are normalized in their original proportions; completion
metrics reference the latched values. The inherited metrics task ID is repaired.

## Reproducibility and acceptance

`python -m scripts.generate_traditional_titration_vr_r15` creates the new package
from the retained r1.4 handoff and embeds the same dependency-free policy source
used by unit tests. It rejects an existing output folder. Controller, policy,
source-scene and physical-comparison hashes accompany the package.

`python -m scripts.validate_traditional_titration_vr_r1 --root <r15-package>
--output <report>` selects the new checks by policy version, preserving the
older task validation path. Each cold start exercises measured joint angles,
both timing anchors, actual shader colors, interrupted closing, low-angle-only
success, completion latching, overshoot failure, exhaustion and reset. Timing
error is limited to one 60 Hz step; float shader comparisons use 1e-5 tolerance.
These are prescribed-joint integration checks, not robot-policy results.

`python -m scripts.render_titration_liquid_comparison --root <r15-package>
--baseline <r14-package> --variant after --linear-states` renders four volume
states with matching cameras. They are static visual snapshots; runtime traces
are separate evidence of timing. Rendering edits only temporary/session layers.

Finalization requires three passing Isaac Sim 4.5 reports on the exact final
scene SHA, matching physical audit, four-state render evidence and a local
visual review tied to the render manifest. ZIP dependency closure, CRC and SHA
must pass. Only then does the current task head advance to r1.5; r1.4 remains.

Output: `outputs/scientific_workbench_traditional_acid_base_titration_vr_r1_5_20260907/`.

## Final result

Three fresh Isaac Sim 4.5 cold starts passed on scene SHA
`3db4835aa1efd4f34171e052da52da6abf4a3a8ea53e92864099a528eda690c7`.
At 45 degrees the measured pale interval was 11.7–13.2 s (1.5 s);
at 90 degrees transition began at 5.0 s and pale pink at 5.5 s.
All timing deviations fit one 60 Hz simulation step.

`make check` passed with 934 tests and one skip; the final nine r1.5 focused
tests also passed. Ruff, package smoke and phase10x smoke passed.
Twelve 1920×1080 images cover four color states from three cameras. Local
visual review accepts the revision with a warning about inherited dark glass
reflections; it is not an independent review or a timing recording.

The only composed scene edits are the controller script and three new policy/
completion attributes. Dependency files are byte-identical to r1.4. Package
closure and ZIP CRC/SHA passed. The VR current head advances to r1.5; r1.4
is retained as the build source, and the robot-validation head is unchanged.

## Color teaching guide addendum

The handoff includes `COLOR_GUIDE_CN.md`, sourced from
`docs/operations/titration-r15-color-guide.md`, with a README link. The builder
copies the guide for future builds. It documents exact Shader/mesh/controller
paths, the live and offline read distinction, six verified interpolation
examples, constant endpoint RGB, and the inactive opacity compatibility values.
This is a documentation-only package update; the scene SHA and its existing
three runtime reports remain unchanged. The ZIP and checksum are regenerated.

The guide update passed the package-inclusion regression test and `make check`.
Both Python snippets compile; their read operations were checked on the actual
USD Stage, and six RGB interpolation examples were verified against the policy.

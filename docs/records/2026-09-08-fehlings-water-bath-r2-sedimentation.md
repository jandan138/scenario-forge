# Fehling water bath r2: 30/60/3-second visual sedimentation

## Contract

An independent r2 package consumes the September 7 r1 delivery. The unchanged
60°C preheated-bath declaration is a teaching assumption; neither thermal
transfer nor chemical kinetics is solved. The same geometric immersion/withdrawal
predicate and 3-second, 2-cm-radius observation rule are retained.

Cumulative valid immersion now caps at 60 s. Up to 30 s the sample stays blue;
30–45 s linearly blends blue to orange-brown and raises opacity from .55 to .80;
45–60 s blends to near-clear and lowers opacity to .25. Completion of heating
and the final appearance coincide at 60 s. Withdrawal followed by stable
observation latches success. Invalid immersion pauses rather than resets.

The bottom sediment grows from zero to a nominal .3 mL over 30–60 s; its height
is obtained by inverting the original cavity-profile frustum volumes. It fades
in over 30–33 s, then stays opaque with brick-red (.70,.18,.07) RGB and .65
roughness. The upper sample's bottom follows the growing sediment; the original
sample top is fixed. Body and surface mesh prims retain fixed topology (64 radial
segments, 32 axial segments). A 20 µm radial inset keeps geometry inside the
profile and a 10 µm interface gap prevents coplanar overlapping surfaces.
The hidden zero-progress sediment retains a nondegenerate 1 µm placeholder.
These are visualization volumes, not stoichiometric or mass-balance claims.

## Ownership and interfaces

The producer's capless tube, all dependency bytes, scene layout, physical
attributes and the existing 969-particle bath remain unchanged. Scenario Forge
owns only visual geometry, two sample/sediment materials and task policy.

`fehlings_r2_state.py` contains dependency-free time and geometry functions.
The generator embeds it with the original immersion predicate and
`fehlings_r2_usd_controller.py`; the original r1 functions remain available to
r1 but are not embedded as duplicate obsolete definitions in r2.

Telemetry remains on `obj_sample_tube`; `fehlings:policy_version` is
`visual_sedimentation_v2`. `color_progress` now means progress through 30–60 s.
Added attributes are `reaction_stage`, `sediment_progress`, `sediment_height_m`
and the cavity profile used by the geometry policy. Explicit relationships
resolve the Sample/Sediment Shader, body and surface nodes after VR remapping.
Reset updates telemetry and visuals immediately, even without a readable rigid
body pose, and returns before accumulating time in that step. Missing pose
otherwise freezes progress without falling back to static USD transforms.

The new task/config/metric references use heat_60s and 30/60/3 seconds.
`COLOR_GUIDE_CN.md` teaches exact paths, material parameters, actual geometry
updates and the difference from the titration task's OmniGlass parameters.

## Validation

Tests cover continuous 30/45/60 boundaries, no early completion, pause/resume,
observation interruption, success latch, fixed sediment floor, growth, cavity
containment, fixed sample top, geometry separation, topology, bindings,
physical invariance and reset without a physics pose.

Each fresh Isaac 4.5 run records actual mesh points/visibility, Shader values,
particle positions, tube pose and new telemetry at 0, 29.9, 30, 37.5, 45, 52.5,
60 seconds, withdrawal and reset. Numeric checks compare every retained
material/geometry state to the policy. Runtime rendering replays retained
geometry as well as colors/poses/particles; it does not invent geometry states.
This is a prescribed kinematic trajectory fixture, not a robot-grasp result.

Finalization requires three distinct exact-scene passing reports, r2-specific
checks, source-bound renders and visual review, physical audit, dependency
closure, ZIP CRC and SHA. The r2 writer is selected during finalization to avoid
accidentally restoring the r1 120-second instructions.

Output: `outputs/scientific_workbench_fehlings_reducing_sugar_water_bath_vr_r2_20260908/`.
Build with `python -m scripts.generate_fehlings_water_bath_r2`; validate/render
with the existing Fehling tools; finalize with
`python -m scripts.finalize_fehlings_water_bath_r2`.

## Final results

Three distinct cold starts passed on scene SHA
`564c21bd4351fec6308faebb303b622eadae522574e40d48eb6c0689747fe6b2`,
including all actual material/geometry checks. All 969 water particles were
retained with none below the beaker. Sample top stayed fixed, and final sediment
height was about 10.112 mm above its fixed bottom.

`make check` passed with 946 tests and one skip; the final 10 focused Fehling
tests passed. The guide reader was verified on the actual disk Stage.
Ten source-bound renders include an actual intermediate-withdrawal snapshot
to distinguish orange-brown clouding from the clearer final supernatant.
Local visual review accepts the result with the inherited in-water refraction
contrast warning; the blue/cloudy/clear distinction is easiest after withdrawal.
The review is not independent, and images are paused replays, not live video.

ZIP CRC/SHA and dependency closure passed. Finalized task/config documents were
checked again for 60-second completion. The Fehling current head advances to r2;
the original water-bath task, r1 Fehling source and titration r1.6 remain retained.

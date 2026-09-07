# Fehling visual-reaction water-bath VR task

## Agreed task

This is an independent derivative of the September 2 water-bath package, not an
in-place revision. A single open 15 mL centrifuge tube substitutes for a glass
test tube. It starts with about 3 mL of pre-mixed visual sample. It is a VR
teaching demonstration, not a claim that the substitute vessel reproduces a
textbook procedure or that chemical kinetics/heat transfer are simulated.

The operator holds the tube throughout heating. Valid simulation-time immersion
drives a deterministic shallow-blue → brown → brick-red appearance over 30 s,
including a nonphysical bottom sediment layer. Heating must still accumulate
120 s before withdrawal. Out of water, within 20° of upright and within a 2 cm
position radius for 3 s completes observation. Return-to-rack is not required.
Invalid immersion pauses rather than resets progress; reset restores all
reaction state and material appearance. No robot-grasp claim is made.

## Ownership and implementation

ConvertAsset derives and qualifies the capless body. Scenario Forge consumes
that package, retains the original room/table/rack/hotplate/beaker placement,
and authors only task visuals and an embedded graph. The new task retains the
main `obj_*` paths and updates task identity, task YAML, VR config and metadata.

`fehlings_state.py` is simulator-independent and tested directly. Its text is
embedded with `fehlings_usd_controller.py` in the USD ScriptNode. There are no
runtime imports from this repo. Physics-step delta time drives accumulation;
dynamic-control poses are used for the single rigid tube, never static USD
pose fallback. Telemetry lives on `obj_sample_tube` as `fehlings:*` attributes.

Immersion checks require sample top at least 3 mm below water, mouth at least
10 mm above water, body within the bath footprint, and clearance above the
beaker floor. The fixed water reference is 0.8793 m, based on a 10 s settled
measurement (q95 about 0.87927 m), not the initial highest particle at 0.89034 m.
The water remains 969 PBD particles with unchanged collision/solver settings.
Only water appearance is changed: near-clear tint (0.95,0.98,1), opacity 0.16,
zero emission. Selected glass/sample meshes use no-cast-shadow visual overrides
to avoid opaque-shadow approximation obscuring the reaction. No physical
attributes are changed by those overrides.

## Diagnostics and evidence boundaries

An initial adversarial fixture teleported a 35° tube into the bath and spilled
water; that run is retained outside the delivery and is not a passing episode.
The corrected fixture tests rejected tilt in free space; a pure predicate test
separately isolates tilt rejection. It then smoothly inserts the upright tube
and records all particle positions and reaction values at milestones.

Passing integration fixtures retain 969/969 particles and no below-beaker
particles through the full heating/observation/reset path. They are kinematic
prescribed tube trajectories, not robot or human VR recordings. Realistic
off-axis collision robustness is not established by those tests.

Images are Isaac 4.5 renders replaying exact retained milestone states in a
paused physics stage. They are not live-camera physics captures or invented
color keyframes. Initial, 10 s, 30 s, 120 s and observation states are retained.
The source beaker's hidden collision proxy still emits a normal-buffer warning;
no warning suppression or local collision repair was introduced.

## Delivery

Output family:
`outputs/scientific_workbench_fehlings_reducing_sugar_water_bath_vr_r1_20260907/`.
The handoff folder contains `scene.usd`, `task_config.py`, task/metric references,
dependencies, README and evidence. Use Isaac Sim 4.5 and allow script nodes.
The configuration's old 5 s task semantics are replaced with 30/120/3 s values.
Metrics remain portable references, not an enabled benchmark evaluator.

Finalization requires three exact-scene passing reports, producer qualification,
render-source binding, dependency closure, ZIP CRC and SHA. Old water-bath and
titration deliveries remain unchanged.

Final scene SHA: `1b240e2a3fa827ee2d91314d9d5347d1ec2a66c7cafaf908827116e8ba235e1b`.
All three release cold starts pass with 969/969 retained particles, zero below
the beaker, and about 1.364 mm rack-start tube settling. Local visual QA accepts
the blue/red-brown distinction with a grey-tube contrast caveat. Closure and
ZIP CRC pass; SHA is distributed beside the approximately 101 MiB ZIP.

# Traditional acid-base titration VR r1

`scientific_workbench_traditional_acid_base_titration_vr_r1` is the first
formal VR scene for the new traditional titration task. It combines the
ConvertAsset-promoted fixed-base titration station with the standard gray
2000×800×755 mm workbench, the replaceable wet-chemistry Code-as-Room
background, an admitted magnetic stirrer, and the dynamic SDF conical flask.

The flask begins on the already-running stirrer. Its solution and stir bar are
visual-only children: no PBD particles, rigid body, collision, or falling
droplet/stream is authored. The stir bar has a continuous visual rotation. Four
precompiled receiver appearances avoid live material-compilation lag; the
station state machine selects colorless, transition, pale-pink, or deep-pink
visual state while lowering the burette column.

The required valve sequence is OPEN → FINE → DRIP → CLOSED. Success requires
14.7–15.3 mL and a closed pale-pink hold of at least three seconds. Overshoot
does not end the episode immediately, but it latches final failure. The VR
configuration inserts the robot at runtime, registers the station root and all
rigid links, and randomizes only the station/stirrer/flask roots as one local
±0.01 m group.

The release gate covers the promoted asset behavior, materialized package,
dependency closure, fixed-camera Isaac renders, and three robot-free Isaac Sim
4.5 cold starts. It does not claim Lift2 policy success, benchmark success, or
true chemical simulation.

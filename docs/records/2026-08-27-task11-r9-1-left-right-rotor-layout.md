# Task 11 r9.1 left/right rotor layout

Task 11 r9.1 changes only the two opposed rotor socket indices from r9's
front/back pair `18/6` to `3/15`. The latter pair is closest to the horizontal
screen axis of the established Task 11 review cameras, so the two red caps read
as left/right rather than near/far.

The base generator now accepts optional primary/balance socket indices while
retaining `18/6` defaults for reproducible r8/r9 builds. r9.1 is emitted to
`outputs/scientific_workbench_task11_vr_r9_1_left_right_20260827/` without
overwriting r9.

All other scene content is unchanged: the visual-fitted centrifuge, eight
single-rigid threaded red-cap 15 mL tubes, two visual-static liquid inserts,
mixed rack, 50 mL context tubes and tabletop dressing remain intact. Robot,
Task 11 and benchmark success stay false.

Qualification covers three Isaac Sim 4.1 static cold starts, robot-free OPEN and
STOP mechanics, package-local GenManip composition and a matched open-lid
visual review of the socket pair.

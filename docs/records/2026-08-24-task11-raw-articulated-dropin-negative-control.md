# 2026-08-24 Task 11 raw articulated drop-in negative control

This handoff is a deliberate negative control for reviewing the original
centrifuge archive without ConvertAsset normalization. It derives from the
stable Task 11 r5 scene and replaces only `/World/obj_centrifuge` with a direct
package-local reference to the archive's `centrifuge_articulated.usda` at
`/LabSpinX8`. The raw articulated layer, main USD, and texture are byte-exact;
the scenario layer authors only the placement transform.

The five original joint prims are preserved. No collider, mass, inertia, drive,
animation cleanup, joint disable, or physics repair is authored. Isaac Sim 4.1
therefore reproduces the direct-GUI-drop behavior: links with inherited Blender
animation are converted to kinematic bodies, the articulation is rejected, and
all five joints fail creation between static bodies. The raw centrifuge has no
colliders, so both dynamic rotor tubes fall about 0.272 m during the two-second
diagnostic.

The report status is `expected_failure_observed`, not `pass`. This package is
only for leadership review of the raw source behavior and must not be used for
VR collection, benchmark evaluation, or robot-policy claims.

The output is
`outputs/scientific_workbench_task11_raw_articulated_dropin_20260824/`; the ZIP
is `handoff/scientific_workbench_task11_raw_articulated_dropin.zip`. Task 11 r5
remains the usable handoff.

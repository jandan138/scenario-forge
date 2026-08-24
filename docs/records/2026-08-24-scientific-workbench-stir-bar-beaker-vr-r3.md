# Stir-bar/beaker VR r3 quick integration

Scenario Forge derived
`scientific_workbench_insert_stir_bar_into_beaker_vr_r3` from the r2 VR
package without changing its task-object layout. The new package adds the
admitted magnetic-stirrer package as `obj_magnetic_stirrer` on the right side
of the workspace and reuses the Task02 fill40 liquid producer artifact in the
beaker.

The liquid contains 816 particles. Its producer measured a 0.4413 fill ratio.
The VR config groups the beaker with `fluid_runtime` for local ±0.01 m
randomization, groups the tray with the stir bar, and randomizes the stirrer
and existing context objects independently. The stirrer is context-only: this
package does not claim magnetic stirring, heating, robot-policy success, or a
complete canonical Task04 rollout.

The r2 scene did not carry the GPU PhysX scene opinions needed by the new PBD
content, so r3 authors GPU broadphase/dynamics, TGS, 120 Hz, and the particle
contact capacity on `/World/physicsScene`. The dynamic beaker cannot consume
the producer's visual-mesh SDF path reliably in this composition. r3 therefore
enables the beaker asset's existing unified PBD convex-decomposition proxy and
disables the visual collision meshes. No asset package is modified.

One Isaac Sim 4.1 three-second integration run passed: all four foreground
rigid objects settled, all 816 particles remained, 99.14% of particle centers
were within the beaker visual AABB, none fell below the table, and the selected
hard-error scan was empty. Three initial-scene views were rendered. Local
visual review found the layout clear and free of visible interpenetration;
the transparent liquid/glass combination reads dark under this room lighting,
which is a rendering caveat rather than a layout blocker.

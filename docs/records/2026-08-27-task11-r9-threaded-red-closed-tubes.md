# Task 11 r9 threaded red closed tubes

Task 11 r9 is generated into
`outputs/scientific_workbench_task11_vr_r9_20260827/` without overwriting r8.

All eight 15 mL objects are replaced by the promoted ConvertAsset
`/ThreadedTube15RedClosed` assembly: two balanced rotor tubes and six rack
background tubes. Each object has exactly one dynamic rigid body. The cap is
the newer source-geometry closed-top threaded cap with the Task 11 red PP
appearance; it is fixed under the tube root and cannot separate. The two 50 mL
background tubes remain unchanged.

Primary and balance tubes retain the r8 blue visual-static liquid. It has no
particle system, collision, rigid body or mass and follows the container root.
Object paths, VR `obj_prim_list`, and local `+/-0.01 m` randomization remain
compatible with r8.

Three isolated Isaac Sim 4.1 scene runs passed for both rotor tubes and all six
rack tubes. Robot-free centrifuge checks also pass: rotor interlock, OPEN-driven
lid motion and hold, and STOP power-off. The GenManip adapter preserves the
exact r9 scene with package-relative dependencies.

The release remains a scene-qualified, robot-unvalidated candidate. It does
not claim cap tightening, robot policy, canonical Task 11 completion, or
benchmark success.

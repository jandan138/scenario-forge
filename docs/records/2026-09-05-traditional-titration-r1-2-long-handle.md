# Traditional titration r1.2 long-handle integration

Scenario Forge now accepts a parameterized titration task identity and consumes
ConvertAsset's promoted `traditional_titration_station_r2` package.  The r1.2
scene contains the visible 90 mm stopcock without any Scenario Forge geometry,
collider, joint, mass, or drive patch.

The VR scene passed three Isaac Sim 4.5 cold starts, one-DOF articulation
initialization, endpoint/overshoot/reset state-machine checks, dependency
closure, and four-view visual QA.  The long handle is visible and proportionate
in both overview and stopcock close-up renders.

The separate Lift2 validation bundle remains fail-closed.  Isaac Sim 4.1
retains one complete robot-controlled semantic success at 15.018 mL and one
motion-only 42.2°→3.7° open/close success, but subsequent runs failed the
reverse stroke and neither PhysX tensor nor contact-report events produced
usable pair-filtered contact evidence under this GPU dual-arm composition.
The required 3/3 gate was therefore not met and Isaac 4.5 command replay was
not attempted.

Outputs:

- `outputs/scientific_workbench_traditional_acid_base_titration_vr_r1_2_20260905/`
- `outputs/scientific_workbench_traditional_acid_base_titration_vr_r1_2_robot_20260905/`

The scene package claims asset and state-machine qualification only.  The robot
bundle is `robot_validation_blocked`; scripted-oracle, robot-policy, benchmark,
and cross-runtime replay success remain false.

## Single-episode visual demonstration

A later recording retained one continuous successful Isaac Sim 4.1 episode as
two synchronized views and a 1920x720 side-by-side MP4.  It reaches 15.063 mL,
shows the pale-pink endpoint, and holds closed for 6.97 s without device-joint,
volume, color, or task-object pose writes.  A gripper-open, lift-offset control
keeps the receiver colorless at 0.0 mL.  This adds
`single_episode_visual_demonstration=true` but deliberately leaves the package
status and all formal robot/benchmark claims unchanged.

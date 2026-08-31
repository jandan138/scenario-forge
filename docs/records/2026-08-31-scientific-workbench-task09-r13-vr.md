# Scientific Workbench Task 09 r13 VR

## Delivery

Final archive:

`outputs/scientific_workbench_task09_r13_3_20260831/handoff/scientific_workbench_task09_r13_vr.zip`

The Task 09 target remains the beaker, matching the pinned Feishu design. The
empty conical flask is also dynamic, SDF-colliding, and graspable, but it is a
non-scoring context/alternate object. No PBD particles are included.

## Layout

- standard `2.0 x 0.8 x 0.755 m` table at the original pose;
- compact oven cart at `[1.51, 0.0, 0.0]`;
- materialized oven at `[1.51, 0.0, 0.755]`;
- target beaker at `[0.62, -0.16, 0.755]`;
- graspable conical flask at `[0.40, 0.14, 0.755]`;
- VR robot pose `[0.85, -1.02, 0.31]`, facing the table/cart seam.

The oven and cart share the same local ±0.01 m randomization group. Each vessel
has its own local ±0.01 m group. The VR config contains no robot friction,
contact-offset, or rest-offset overrides.

The oven starts powered, idle, and not heating at 60°C. The formal workflow is
open door, pick and place the beaker, close door, turn to 65°C, and physically
press the knob to start heating. The ten Feishu progress weights are preserved.

## Evidence

- ConvertAsset cart: six standard support probes and three 100 kg load runs;
- ConvertAsset oven: three full producer interactive smokes;
- final scene: 300 Isaac Sim 4.1 Play updates with stable cart, oven, beaker,
  flask, and powered-idle 60°C control state;
- four 1280×720 render views and local human-style visual QA pass;
- dependency closure: 17 layers, five external assets, zero unresolved paths,
  and zero non-package absolute assets.

The first two render attempts placed cameras in room geometry and were rejected;
the accepted retakes are the only images included in the final ZIP. The final
package does not claim robot-policy, benchmark, or thermal-process success.

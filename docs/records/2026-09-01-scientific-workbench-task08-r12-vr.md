# Scientific Workbench Task 08 r12 VR

Task 08 r12 is a VR action-collection candidate with one scored tube/cap pair
and two physically interactive background alternatives. Three open long-neck
threaded 15 mL tubes begin in adjacent slots of the scaled 18+4 mixed rack. Three
closed red threaded caps begin on the admitted 30 cm steel tray. The middle pair
is the configured target.

The rack consumes the ConvertAsset r3 package with baked `(1.1, 1.1, 1.3)`
scale, visual-mesh SDF and eighteen primitive slot-bottom supports. Its scene
root directly authors translate, orient and unit scale so GUI edits remain
available before Play. Tube locations are generated from package named frames.

Every tube uses the unified nine-input webpage-standard glass visual and contains
an 80% blue visual-static liquid mesh. Each liquid is a child of its tube and has
no particle system, rigid body, collision or mass. All six tube/cap objects are
dynamic and appear in the VR object list. The task config intentionally omits
robot material, contact-offset and rest-offset patches.

Three independent Isaac Sim 4.1 eight-second runs pass. Tube radial motion is
about 0.011 mm, upright angle about 2 degrees, all caps remain on the tray, and
the final-second maximum displacement is zero. Fixed before/after views pass
local visual review. The source USD has `/World` as defaultPrim, direct `obj_*`
children, a texture-free opening light and zero unresolved dependencies.

The handoff is
`outputs/scientific_workbench_task08_vr_r12_20260901/handoff/scientific_workbench_task08_vr_r12_candidate.zip`.
This release claims VR action-collection layout readiness and static stability.
It does not claim physical screw advance, released-cap retention, Task 08
success, robot-policy success or benchmark success.

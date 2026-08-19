# 2026-08-18 HCI 15 mL Closed Insert and Lid Demo Admission

## Outcome

Scenario Forge issued a ConvertAsset admission request for a **kinematic**
insert-and-lid-close demonstration on the existing HCI955350 mini centrifuge.
The portable request is
[`../operations/scientific-workbench-hci-15ml-closed-insert-lid-admission-request.yaml`](../operations/scientific-workbench-hci-15ml-closed-insert-lid-admission-request.yaml).

This round does not compile a desktop prototype package and is not Feishu
Task 10.

## Why this tube is not real 15 mL size

The HCI rotor holes are about 12.5–13.3 mm inner diameter. Closed-lid clearance
above the rotor is about 4 mm. The lab-library 15 mL red-cap assembly is
16.68 mm body OD, 20.84 mm cap OD, and 119.7 mm tall with the cap on.

A real-size 15 mL tube cannot enter those holes, and a tube that sticks above
the rotor hits the lid. Enlarging the whole centrifuge enough for an unscaled
15 mL tube would make a ~0.6–0.8 m machine, which is out of scope.

The 15 mL red-cap asset has **no helical thread mesh**. The cap is a separate
shell; Blender/URDF only animate two turns plus a lift. Welding the cap to the
body for this demo does not destroy thread geometry.

## Why non-uniform scale

Uniform shrink to the already-qualified 43.8 mm test-tube envelope would also
fit, but would make the cap much thinner than the hole. The request instead
bakes:

- radial `k_d` in `[0.50, 0.55]` so the **cap** (not only the body) clears the
  hole with 0.5–1.5 mm radial gap;
- height `k_h` in `[0.33, 0.37]` so assembled height is about 40–44 mm and the
  closed tube sits entirely in the well.

The facade must bake that scale into the mesh. The package root scale stays
identity. This is an explicit exception to `uniform_geometry_scale_only` and
applies only to this closed HCI-fit tube. Do not reuse it for cap tightening.
Do not reuse the k=0.365 Taoyuan test-tube qualification hashes.

## Acceptance

ConvertAsset must return, on Isaac Sim 4.1:

1. `socket_insertion_clearance: pass` for the new closed tube;
2. `lid_contact_cycle: pass` with that tube at the inserted target and zero
   tube–lid contacts;
3. a scripted kinematic **mp4** of lid open → tube insert → lid close.

The video is a real Isaac viewport/RTX recording, not a robot-policy episode.
Scenario Forge does not add an episode runner. The mp4 stays outside git per
[`../operations/artifact-policy.md`](../operations/artifact-policy.md); the
producer returns its path and SHA-256.

## Claim boundary

This request does not claim Feishu Task 10/11 success, setting/lid-open/shutdown
buttons, robot grasp or insertion policy, eBench/VR package generation, or
real-world 15 mL centrifuge pairing.

# Task 02 r8.4: world-baked PBD state and preloaded support

## Outcome

Task 02 r8.4 is a physics-qualified **candidate package**, not a robot-success
release. It retains the r7 task semantics and consumes the ConvertAsset GPU-PBD
transfer-pair handoff without copying conversion logic into Scenario Forge.

The generated package is:

`outputs/scientific_workbench_task02_r84_20260815/`

## Two integration defects closed

1. Isaac Sim 4.1 did not apply the parent `Xform` translation to the authored
   particle simulation points in this composition. The generator now translates
   the qualified 548-point initial state into final world coordinates and gives
   the source and target actors explicit final poses.
2. GenManip performs a 100-step warm-up during scene initialization. In the r8.3
   composition the task table arrived only through later recovery data, so the
   dynamic containers and liquid had no support during warm-up. r8.4 references
   the same r7 table in the initial USD composition. Recovery may encounter the
   same path later, but does not create a second table.

The generator also removes task-config global robot contact/rest offset
preprocessors. Robot-global collision inflation is not an acceptable substitute
for an asset-specific qualified collision model.

## Runtime observation

The latest successful cold probe retained the particle cloud after initialization,
recovery, and 40 additional physics steps. The observed world-space particle Z
range was 0.767981--0.776026 m, at the bottom of the qualified source cylinder,
instead of falling through the absent table.

## Claim boundary and remaining work

This closes package composition and initial fluid retention only. It does not
claim robot contact grasp, five-stage pour completion, 3/3 cold-run stability,
video evidence, policy success, benchmark success, or active liquid metrics.
Those claims belong to the consumer-side EOS evidence workflow. EOS has now
repeated a true-contact grasp of the qualified loaded cylinder with all 548
particles retained. The best measured retained lift is 95.10 mm rather than the
required 100 mm. Robot evidence therefore remains blocked.

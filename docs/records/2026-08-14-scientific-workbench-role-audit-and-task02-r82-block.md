# Scientific workbench role audit and Task 02 r8.2 block

Date: 2026-08-14

Scenario Forge declared a two-phase role admission request for the 29 single
assets in `实验室资产库.zip`. The six combination scenes remain excluded. The
portable request is
`docs/operations/scientific-workbench-asset-library-role-admission-request.yaml`.
ConvertAsset owns mesh analysis, repair, collision cooking, runtime gates, and
promotion; Scenario Forge does not reproduce that logic.

The consumed ConvertAsset audit reports 13 Phase-1 assets and 16 Phase-2
assets. Only the 100 mL and 250 mL graduated-cylinder primary meshes require
the strict dual-rim annular topology repair. This is a topology inventory, not
runtime admission for the 29 assets.

ConvertAsset also emitted source-bound identity-facade candidates for both
phases. The 16 Phase-2 packages pass a shared three-cold-run, five-update
load/render baseline, but remain `candidate_role_gates_pending`; the baseline
does not substitute for dynamic-tool, support/insertion, or instrument-reset
qualification.

For Task 02, ConvertAsset built a source-bound 250 mL cylinder candidate whose
visible repaired mesh uses `convexDecomposition`. Three cold starts completed
five updates each, but the full Isaac Sim 4.1 gate reported
`Non-GPU-compatible convex mesh is not able to collide with particle system`.
Measured retention was 58/548 (10.58%), target reception was 0/548, tabletop
spill was 548/548, and performance was 77.81 mean FPS at 960x540.

Scenario Forge's upstream-admission loader accepts the audit and rejects the
blocked Task 02 result as non-promotable. Therefore no r8.2 eBench/VR scenario
package, USD, config, or benchmark claim is generated. The existing r8 static
diagnostic remains historical evidence; the task directory now identifies the
r8.2 attempt as blocked before package generation.

Claim boundary: this result does not invalidate the r7 static task layout and
does not prove robot, policy, or benchmark behavior. It specifically rejects
the closed visible-cylinder-mesh convex-decomposition route for GPU PBD contact
in the recorded Isaac 4.1 protocol.

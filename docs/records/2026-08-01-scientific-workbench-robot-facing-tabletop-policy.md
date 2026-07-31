# Scientific Workbench Robot-Facing Tabletop Policy

## Decision

Initial scientific-workbench task equipment is placed in the half of the
table facing the declared robot base, while retaining a hard 0.10 m margin
from every tabletop edge. This is a default that follows the composed scene,
not a fixed source-axis convention.

An explicit `tabletop_placement_exception` may document a genuine far-side
task requirement. It cannot waive the edge margin.

## Implementation

The `scientific_workbench.robot_facing_tabletop.v1` domain policy is evaluated
in the eBench adapter against composed OpenUSD world bounds. Every applicable
package receives `evidence/tabletop_placement_policy.yaml`; a blocked result
prevents its eBench export.

The policy was wired into the layout-prototype, bimanual-pour, tube-prototype,
and background-variant generators. The portable policy calculation itself is
simulator-neutral; OpenUSD inspection stays in the adapter layer.

## V3 Re-layout Evidence

`outputs/scientific_workbench_layout_validated_prototypes_v3_20260801/`
contains re-laid versions of Task Design rows 2, 13, and 16. All three policy
reports pass without exceptions. Their smallest measured tabletop-edge margins
are 0.382 m, 0.360 m, and 0.360 m respectively, above the 0.10 m requirement.

The output also contains static authored-key-state and native GenManip
post-reset/pre-action 1920x1080 renders. A local visual review confirmed that
the task equipment is visibly on the robot side with clear room around it; it
is a composition check only, not an independent review or a reachability,
execution, liquid-transfer, or benchmark-success claim.

The prior V2 output remains preserved for comparison.

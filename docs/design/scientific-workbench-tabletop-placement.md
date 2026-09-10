# Scientific Workbench Tabletop Placement

Status: domain policy interface and rationale. Current placement requirements
are maintained once in [USD-006](../standards/usd-layout.md#usd-006).

## Rationale

Initial task equipment should form a usable robot-facing work area while
retaining deliberate tabletop margins. The rule evaluates composed footprints,
not just object origins, and distinguishes equipment from background dressing.
Its scope and thresholds are defined in USD-006, including the limited side
preference exception.

## Domain interface

The scientific-workbench domain pack declares
`scientific_workbench.robot_facing_tabletop.v1`.
Object metadata may carry `tabletop_placement_exception` for the exception
specified in USD-006; this is not a general override of placement validity.

Scientific-workbench generators write:

```text
evidence/tabletop_placement_policy.yaml
```

The evidence contains the policy version, support-surface bounds, robot base,
applicable object footprints, four edge clearances, robot-side result and
exception metadata. The composed EBench scene is the evaluation input; a blocked
policy result prevents publication under this domain policy.

## Scope and maintenance

The policy concerns initial placement only. It is not evidence of reachability,
grasp quality, collision-free motion, liquid dynamics or successful execution.

2026-09-08: scene-authoring requirements moved to USD-006; domain identifier,
metadata and evidence interface remain documented here. Changes to the policy
need corresponding validation and a synchronized standards update.

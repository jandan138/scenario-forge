# Scientific Workbench Tabletop Placement

## Principle

Initial task equipment belongs in the robot-facing half of the table, but not
on its edge. This makes the workcell look like a usable laboratory bench while
leaving a deliberate safety and manipulation margin.

The rule applies only to task objects initially supported by the declared
tabletop. The room, table, robot, and visual-only background objects are not
task equipment for this purpose.

## Contract

The scientific-workbench domain pack declares
`scientific_workbench.robot_facing_tabletop.v1`.

- The full visual footprint of every applicable object must remain at least
  **0.10 m** inside every tabletop edge. This is a hard gate.
- The robot-facing half is the half of the tabletop reached by the horizontal
  vector from the tabletop centre to `robot.spawn`. It is not a hard-coded
  world axis, so the rule remains valid when a room or table is rotated.
- An object outside that half is blocked unless its object metadata contains a
  non-empty `tabletop_placement_exception` string. That exception records a
  task-specific reason and waives only the side preference; it never waives the
  0.10 m edge gate.

Scenario Forge evaluates the composed EBench scene's world-space tabletop and
object bounds. It does not infer safety from object origins, hand-authored
coordinates, or a source asset's uncomposed bounds.

## Evidence and Scope

Scientific-workbench generators write:

```text
evidence/tabletop_placement_policy.yaml
```

The evidence records the policy version, support-surface bounds, robot base,
each applicable object footprint, all four edge clearances, robot-side result,
and any explicit exception. A blocked result stops package publication.

This validates initial placement only. It does not establish reachability,
grasp quality, collision-free motion, liquid dynamics, task execution, or
benchmark success.

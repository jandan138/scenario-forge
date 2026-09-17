# Validation and acceptance

Do not claim an articulated asset is complete from a render or a successful USD save alone. Run the static contract first, then reopen and run Isaac runtime checks.

## Acceptance stages

### A. Static contract

Run `scripts/check_articulation_usd.py` under the target Isaac Kit Python. It must report:

- one `ArticulationRootAPI` within the supplied asset root;
- fixed mode has one root fixed joint to the world, or floating mode has one declared root body;
- body0/body1 relationships form one connected parent-child tree;
- no unannotated loop or unsupported included joint;
- no child world anchors;
- explicit mass/inertia, collision, units, up axis, and stable root paths;
- no negative-scale collision geometry.

Any `FAIL` blocks runtime acceptance. A justified excluded loop may be `WARN`, but the report must include the exception reason and affected paths.

### B. Reopen and self-containment

Save the USD, close the stage/process, and reopen it in a fresh Isaac context. Confirm that:

- the default prim and asset root resolve;
- all visual meshes, collision proxies, materials, and textures resolve without personal absolute paths;
- the root API count, link count, joint count, limits, drives, and initial states are unchanged;
- no session-layer-only edits are required for the intended default behavior.
- Enumerate every supported VariantSet after reopening the distributable binary and verify
  that each selection changes a composed opinion (material binding, visibility, collider
  count, kinematic state, or equivalent), rather than merely exposing a selector name.
- Measure root and component world bounds from the reopened stage. Configuration values are
  expectations and provenance, not geometry evidence.

### C. Isaac 4.5 runtime

Isaac 4.5 is the full runtime target. At minimum, run:

1. **Root discovery:** exactly one articulation is returned for the asset root by the available `Articulation`/`ArticulationView` interface.
2. **State initialization:** all declared initial joint states are applied without posing non-root links directly.
3. **Motion:** each revolute/prismatic DOF moves in both intended directions, respects limits, and returns to rest without unacceptable residual error.
4. **Resistance:** drive damping and rigid-body damping produce the intended response without ignored-friction warnings.
5. **Contact:** visual/collision separation, closed-state clearances, support surfaces, and self-collision policy pass.
6. **Load:** load-bearing links remain supported under the declared mass and frame count.
7. **Release/extraction:** removable links travel through the declared release range without unintended drop or residual constraint.
8. **Drift:** the fixed base remains stationary and no unrelated link accumulates unacceptable pose drift.
9. **Variant coverage:** every supported handedness/mode variant passes the relevant checks.

Record numerical thresholds in the asset-specific report; do not invent universal mass, force, gap, or frame values in this skill.

### D. Isaac 4.1 static audit

Run the same USD/schema/topology checks where Isaac 4.1 is available. Label the result `static_audit_only` unless a real 4.1 simulation was run. Never report a 4.1 runtime pass based on a 4.5 result.

## Direct force versus robot integration

Direct handle/knob/button forces are useful smoke tests for joint limits, drives, collision, and drift. They do not prove that a particular robot, gripper, grasp planner, controller, or contact sensor will succeed. Reports must separate:

- `physics_smoke`: direct forces and deterministic scripted states;
- `robot_integration`: actual robot/grasp/contact tests, if available;
- `not_tested`: capabilities not exercised.

## Report shape

Use a stable JSON or Markdown summary with at least:

```json
{
  "assetRoot": "/World/Asset",
  "mode": "fixed",
  "articulationRoot": "/World/Asset/Joints/BaseToWorld",
  "implementationStatus": "PASS|FAIL|PASS_WITH_WARNINGS",
  "isaacRuntime": "4.5|not_run",
  "staticAudit": "PASS|FAIL",
  "counts": {"links": 0, "revolute": 0, "prismatic": 0, "fixed": 0, "colliders": 0},
  "checks": [],
  "exceptions": [],
  "limitations": []
}
```

Include the generator revision, source mesh hash, Hunyuan parameters, test seed, and report timestamp. Keep machine-specific paths out of the reusable skill.

## Regression fixtures

The minimum static fixture set is:

- valid one-root fixed-base tree;
- two root APIs;
- child world anchor;
- reversed body0/body1;
- included loop;
- excluded loop with a reason;
- missing mass/collider;
- negative collision scale.

Use a temporary copy of the historical oven or a small synthetic mechanism for runtime regression. The original oven USD remains unchanged and is expected to be labeled a legacy joint-graph example rather than a new single-root pass.

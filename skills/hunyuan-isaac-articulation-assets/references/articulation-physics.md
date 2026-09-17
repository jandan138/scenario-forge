# Single-root articulation physics

This reference defines the physical topology for complex articulated assets. It intentionally generalizes the oven lessons; asset-specific dimensions and tuning belong in a case study.

## Canonical topology

Use one articulation per asset scope, not one articulation for an entire scene. A fixed-base asset should have a shape equivalent to:

```text
/World/<AssetId>                         (asset container, one default prim)
├── Links/Base                            (rigid-body root link)
│   ├── Visual/*
│   └── Collision/*
├── Links/<ChildLink>                     (rigid-body links)
├── Joints/BaseToWorld                    (PhysicsFixedJoint + sole ArticulationRootAPI)
└── Joints/<JointName>                    (revolute/prismatic/fixed articulation joints)
```

The USD hierarchy is for organization; the articulation graph is defined by each joint's body relationships. For every included joint, `body0` is the parent link and `body1` is the child link. Every non-root link has at most one included parent joint. The graph must be connected and acyclic unless an explicitly excluded loop-closing joint is being used.

For a fixed-base object:

1. Make the base a rigid-body root link with explicit mass/inertia (it may be immobile because it is fixed to the world, but it is not a separate static body outside the articulation).
2. Create exactly one world fixed joint for the asset.
3. Apply `UsdPhysics.ArticulationRootAPI` to that root fixed joint. Do not apply another root API to a wrapper, child link, or independent mechanism.
4. Connect doors, lids, handles, knobs, buttons, shelves, rotors, and other moving parts to the base or to another link with supported articulation joints.
5. Keep purely decorative geometry under the owning link without creating an extra rigid body.

For a floating asset, choose one root link, apply the root API to that link, and state `mode=floating` in the asset report. Do not infer floating mode from a missing world joint.

NVIDIA's articulation documentation describes fixed-base roots on the world fixed joint (or an ancestor) and requires a tree of body relationships; use the root joint placement above as the deterministic convention for this skill: https://docs.omniverse.nvidia.com/kit/docs/omni_physics/108.0/dev_guide/rigid_bodies_articulations/articulations.html

## Joint authoring

For every joint, author and report:

- type (`RevoluteJoint`, `PrismaticJoint`, or `FixedJoint`);
- `body0` and `body1` paths;
- local frame positions and rotations for both bodies;
- axis in the joint frame;
- lower/upper limits in the units expected by the USD schema;
- initial joint state;
- drive type, target, stiffness, damping, and force/torque limits;
- collision policy for the linked bodies;
- the intended physical meaning and an interaction frame.

Use explicit joint frames. Do not rely on visual mesh origins, inherited transforms, or simulator topology inference when the axis or pivot matters. Keep body0/body1 ordering consistent with the parent-child tree so articulation state and measured forces map to the intended link.

Use `PhysxSchema.JointStateAPI` (or the equivalent target-version API) for initial articulated positions and velocities. Once playback starts, set joint state through the articulation interface rather than directly posing non-root links.

### Resistance and drives

Use `UsdPhysics.DriveAPI` damping and rigid-body angular/linear damping for viscous resistance. This is the cross-version pattern validated by the oven project. Do not write `physxJoint:jointFriction` on non-articulation joints; even in an articulation, prefer the drive/damping model unless a target-version test demonstrates a needed alternative and records its warning behavior.

Choose gains from the intended interaction and mass scale, then test both motion directions, rest, limit contact, and reversal. A high stiffness that looks responsive in isolation can produce contact instability or excessive impulses on light links.

For coupled DOFs, prefer articulation-supported mimic joints or tendons when they express the mechanism and the target Isaac version supports them. Record gearing, offset, compliance, and stability tests. Do not close a geometric loop by adding a second unconstrained world joint.

## Collision and contact geometry

- Separate `Visual` and `Collision` scopes for every link.
- Prefer simple boxes, capsules, convex decompositions, or validated SDF/mesh approximations for collision.
- Keep hidden support colliders where visual rails, lips, or shelves do not provide a continuous contact surface.
- Check actual proxy overlap/clearance at rest and throughout travel; an apparently touching AABB can still have a gap along one axis.
- Do not use a shaft or decorative detail as a collider if it intersects a static fascia and blocks the intended joint travel.
- Never use negative scale on physical geometry or collision proxies; build a positive-scale mirrored variant instead.
- Disable self-collision only when the choice is intentional, documented, and covered by the contact test.

For load-bearing/removable parts, test both states:

- **Inserted/loaded:** the link remains supported under gravity and the specified independent load.
- **Extracted/released:** the link travels through its limits without falling through a support proxy or leaving an unintended residual constraint.

## Variants and composition

Use VariantSets for handedness, hinge side, shelf mode, or other approved physical variants. Before writing a variant value, inspect and clear conflicting direct opinions; a stronger direct opinion can make a selector appear to change while the composed physics value remains unchanged. Validate every selected variant, not only the default.

Keep the articulation root and link paths stable across variants. A variant may replace geometry, frames, or joint limits, but it must not silently introduce a second root API or a separate world-anchored body.

## Exceptions

The default is one included articulation tree. An exception is allowed only when one of these conditions is demonstrated:

- an articulation-unsupported joint or topology is required;
- a closed loop cannot be represented by a supported mimic/tendon or tree rewrite;
- a detachable subassembly must become an independent asset at a defined release event;
- a target Isaac/PhysX version has a documented limitation or instability.

For every exception, add a non-empty namespaced reason such as `asset:articulationExceptionReason` directly on the affected joint, identify the affected joint/body paths in that value or a nearby report, state whether the joint is excluded from the articulation, and add a runtime stability test. The static checker should emit a warning for a justified excluded loop and fail an unannotated exception.

## Topology checklist

Before runtime testing, verify:

- exactly one root API in the asset scope;
- exactly one root-to-world joint in fixed mode;
- one connected included graph;
- no included graph cycle;
- one parent per non-root link;
- no child link directly connected to the world;
- all included joints are supported by the target Isaac version;
- all dynamic links have mass/inertia and at least one intentional collider;
- initial states are joint states, not post-playback child poses;
- root/link/joint paths remain stable after save and reopen.

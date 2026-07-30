# 2026-07-31 Articulated Fixed-Base Mounting Consumer

## Decision

Scenario Forge consumes producer-qualified fixed-base placement only from
`manifest.articulation_contract.mounting`. The accepted contract is
`aan.articulated_mounting.v1`; its coordinate semantics are Z-up, metres,
`wxyz`, a support frame in runtime-articulation-root-pose local coordinates,
and a support-plane-to-root pose expressed at zero task yaw.

The final manifest declaration must be a `pass` and must bind the source USD,
packaged device profile, and runtime qualification report by SHA-256. Scenario
Forge also verifies that the same mounting candidate is present byte-for-value
in the packaged profile and qualified report. A partial declaration or a
profile/report/manifest disagreement is rejected.

## Placement

For a qualified `fixed_base` device, the task-authored quaternion is a Z-yaw
choice. Scenario Forge composes that yaw with the producer mount rotation and
rotates the producer mount translation by the same yaw. The support plane is
placed directly on the eBench tabletop: no additional spawn clearance is
added.

The producer support frame is propagated into task-interactive geometry and is
used by preview evidence to measure the real support point. Dynamic rigid
objects continue to use the existing 10 mm settle clearance. This change does
not add object-specific colliders, scale, mass, inertia, joints, or simulator
patches.

Task-interactive geometry carrying this mounting extension uses
`scenario-forge-task-interactive-geometry/v0.2`. The existing v0.1 shape remains
unchanged for non-mounted objects.

## Runtime Geometry Gate

The mounting contract carries producer-qualified warmup and final
world-axis-aligned extents after joint reset. The initial-scene preview request
binds those two extents separately to its `warmup_start` and `post_warmup`
samples. Each sample retains the existing five-percent extent threshold; the
consumer does not substitute the authored closed-state package bound and does
not relax the gate.

The producer reset positions must cover every runtime DOF and match the
articulation contract's semantic reset values. GenManip receives those already
validated reset values through its existing native articulation
`initial_layout`; Scenario Forge does not modify GenManip.

## Claim Boundary

This contract establishes package placement, reset-state geometry, and
structural initial-scene evidence. It does not establish robot-policy success,
task success, benchmark score, or real-world physical calibration.

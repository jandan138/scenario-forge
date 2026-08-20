# Fluid-interaction asset contract

Scenario Forge treats “can interact with GPU-PBD liquid” as an admitted asset
capability, not as a scene-local collider patch. ConvertAsset owns geometry
inspection, collision authoring and Isaac Sim qualification. Scenario Forge
owns review orchestration, strict handoff loading and relocatable delivery.

The v1 contract distinguishes three behaviors:

- `reservoir`: retains liquid while static and moving, then releases it through
  the reviewed opening when poured. Examples are beakers, graduated cylinders,
  flasks and an open 50 mL centrifuge-tube body.
- `conduit`: directs liquid from one reviewed inlet to one reviewed outlet. A
  funnel passes only if at least 90% reaches the receiver through that outlet
  and no particle escapes through a wall or seam.
- `surface_guide`: measurably redirects flow along an external surface. A glass
  rod that does not establish the paired improvement is `not_applicable`, not a
  fabricated pass.

The producer first emits a human-reviewable YAML proposal with source hash,
exact prim, axis, cavity/throat measurements, named frames, geometry roles and
three normalized SDF presets. Qualification accepts only an explicitly approved
proposal. Its fast path reuses source visual geometry with SDF collision and
keeps the r10.3 settings as upper bounds; offsets and margins shrink with the
measured clearance. A failed fast path is diagnostics, not permission to add a
Scenario Forge patch. Package-local derived partitions require a second review
in ConvertAsset.

A promoted package contains an empty fluid-capable asset, not particles. It
claims only `qualified_fluid_interaction_asset`; it never claims robot policy,
metric or benchmark success. Existing liquid-start generation may then compose
the asset and add the pinned Task 02 liquid recipe separately.

Qualification is process-isolated and behavior-specific. Reservoirs require
three cold runs with 99% static retention, 95% motion retention, at least 50%
outflow after a 110-degree pour and four-second hold, and zero structural leaks.
Conduits require three cold runs with 90% legal-outlet delivery and zero
structural leaks. The supported runtime is Isaac Sim 4.1.x; another Kit version
must not inherit the claim.

The proposal also compares a conduit throat with the pinned liquid recipe's
effective particle diameter. A smaller throat is
`particle_throat_incompatible`: widening the collider beyond the visible tube
or silently switching to a different liquid recipe is not an admissible fix.

# Liquid Measurement Adapter Contract

This document defines the capability boundary for liquid-transfer scoring. It is
a contract, not an implementation: Scenario Forge owns the metric declaration;
runtime adapters (GenManip/EOS or future engines) own the measurement.

## Capability

`liquid_sim.contained_volume_ratio`

A runtime advertises this capability when it can report, for a given episode, the
fraction of the source container's initial liquid content that ends up contained
inside the target container. Rubric items that `require` this capability stay
`active: false` until a qualified runtime exists.

## Required measurement semantics

1. **Particle-position readback with region counting.** The only accepted
   measurement path is reading simulated liquid particle positions and counting
   them against container interior regions (source / target / spill). This
   mirrors the LabUtopia `classify_visible_beaker_positions` approach.
2. **Initial snapshot at episode start.** `initial_snapshot: episode_start`
   pins the denominator: the particle count inside the source container at
   episode start, before any action.
3. **Containment ledger, not a final-frame snapshot.** The ratio must be
   computed over a time series of per-step region counts (a containment ledger),
   so transient spills are visible. A final-frame-only ratio is methodologically
   invalid (LabUtopia observed particles leaving and returning mid-episode).
4. **Readback re-pinning after reset.** Some runtimes silently revert particle
   readback flags on `World.reset()`. An adapter must re-assert readback after
   every reset before trusting measurements.

## Explicitly rejected measurement paths

These were evaluated upstream and must not be used as scoring evidence:

- isosurface / render-mesh fluid level (render-only, OOM-prone);
- particle contact reports (not supported by the physics backend);
- visual water-level estimation (not reliable as a scoring basis).

## Vessel prerequisites

Liquid scoring on a container additionally requires a fluid-safe collider
wrapper qualified for that container (target particle count and seed set, static
zero-leak reproduced). The current bimanual-pour vessels are qualified for rigid
SDF collision only; no fluid containment is claimed for them. Activating the two
`liquid_transfer_*` rubric items requires all of:

1. per-vessel fluid-safe wrapper qualification evidence;
2. a runtime adapter satisfying the semantics above;
3. mass/density authority resolved for the simulated particles.

Only then may a package build flip the items to `active: true`. The package
structure does not change on activation — it is a flag, not a new contract.

## Engine portability

The contract names semantics, not APIs. Any engine whose adapter can satisfy the
semantics above may activate the capability; the package and its metrics do not
change. Engines that can only offer the rejected measurement paths are not
eligible until a new capability entry is negotiated.

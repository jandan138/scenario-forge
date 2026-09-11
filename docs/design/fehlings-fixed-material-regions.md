# Fehling fixed material regions (r5, derived from r3)

## Decision

The user requested a simpler visual reaction: retain r3 contact, cumulative
simulation heating time, pause/resume, observation and reset; replace growing
sediment and shrinking upper-sample geometry with two fixed regions whose
materials change over time. The existing r4 CPU-collider branch is not the base.

The lower region occupies one third of the original liquid-column height, not
one third of its volume or of the entire tube. The upper surface remains at the
r3 sample top. Both regions start blue and translucent; a hidden lower region
would leave the truncated upper liquid floating. The lower region gradually
becomes opaque matte brick-red while the upper region clouds then clears.
The agreed height fraction is authoritative: measured against r3 it is slightly
thinner (9.536 mm versus 10.112 mm), despite the earlier qualitative wish for a
thicker sediment. This was reported during implementation; no extra height was
silently introduced.

## Representation and boundaries

The two semantic regions retain the four existing body/surface Mesh paths and
two UsdPreviewSurface materials. The generator authors their geometry once.
Their side boundaries meet at the same z and radius. The upper body has no
bottom cap; the lower region's top surface is the single internal interface,
avoiding coincident surfaces. A faint initial interface contour remains in the
retained glass rendering, so this is not a claim of optically perfect continuity.

The embedded controller contains r3's source-package state/contact functions
and a new material-only appearance writer. It has no volume-to-height,
fitted-region, topology, visibility or Mesh-update logic. Each step writes the
two shaders' diffuseColor, opacity and roughness, plus task telemetry.
The shipped code is self-contained; pure package layers do not import simulator
SDKs. r3 physical contents, source dependencies and placement are retained.

`sediment_progress` now means material development, not volume growth;
`sediment_height_m` is constant even at initial/reset. The new policy identity is
`visual_fixed_regions_v5`, with contact policy `visual_water_contact_v3` retained.
Historical task packages and their telemetry meanings are not rewritten.

## Architecture, completeness and risk review

- **Architecture:** task-local source scripts and a generator, without a new
  core package/schema/adapter contract. Existing geometry/Shader relations remain
  usable; policy identity distinguishes the changed telemetry interpretation.
- **Completeness:** clamped continuous time curves, cloud peak, endpoint,
  pause/resume, success latch and pose-independent reset; the finalizer dispatch
  preserves the new task ID and policy. Replay restores all six changing Shader
  inputs, and captures fixed geometry across the entire reaction and reset.
- **Risk:** the main visual risk is nested transparency and the internal
  interface. Validate withdrawn and in-water views. Physical/content comparison
  and qualified r3 source hash guard the derivation; final evidence binds the
  generated scene, with three fresh runtime processes and closure/ZIP checks.

No fluid motion, granular mechanics, real chemistry, temperature solution or
new CPU-runtime compatibility is implied. The material approach deliberately
shows a fixed region becoming more evident rather than a rising sediment front.

## Evidence and operations

- [Current material standards](../standards/materials-and-liquids.md), MAT-001–006.
- [Task-state standards](../standards/task-state.md), STATE-001–006.
- [Validation and delivery](../standards/validation-and-delivery.md), VAL-001–006.
- [r5 operating and color guide](../operations/fehlings-r5-color-guide.md).
- [Dated r5 evidence](../records/2026-09-11-fehlings-r5-fixed-material-regions.md).

# Articulated Instance Layout — Design Rationale

Status: design rationale and migration entrypoint. The current scene-authoring
requirements live in [Articulation standards](../standards/articulation.md).
They explicitly scope the canonical v2 hierarchy to the qualified fixed-base
route; this document does not define a second copy of those requirements.

## Why the fixed-base v2 route exists

Earlier oven handoffs could preserve links below a Scope-based Instance and use
a kinematic chassis without a complete articulation. Downstream attempts to add
an articulation exposed kinematic-link errors; making a chassis dynamic without
its proper anchor allowed the assembly to move apart. VR post-processing also
needed a transformable boundary rather than a Scope.

The producer-qualified v2 route separates scene placement from device assembly
and makes the base anchoring and runtime registration explicit. Its current
hierarchy and ownership are defined by ART-001/ART-002, and registration and
randomization by ART-003. Source materialization must preserve asset-internal
transforms rather than confusing them with scene placement.

## Evidence and legacy interpretation

See the [fixed-base v2 implementation and oven handoff record](../records/2026-09-04-fixed-base-articulated-instance-v2-and-oven-handoffs.md)
and [VR link registration record](../records/2026-09-04-vr-articulated-link-registration.md).
The v1 validator remains available to interpret immutable historical outputs;
ART-004 defines its boundary relative to new v2 exports.

Mobile-base or other articulation topologies are not qualified by those oven
experiments. New designs need their own stated scope and corresponding evidence
before extending the current standard.

## Rule changes

Propose and explain changes here or in a linked design document. After the
appropriate validation, update the canonical rules using the
[standards maintenance workflow](../standards/maintenance.md), rather than
reintroducing a separate normative hierarchy here.

2026-09-08: moved the previously published authoring requirements to the standards
library; preserved this path, rationale and evidence links. No asset or runtime
implementation changed in this documentation migration.

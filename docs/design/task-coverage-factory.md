# Scientific Workbench Task Coverage Factory

## Purpose

The coverage factory compiles the Feishu Task Design catalog into one canonical,
versioned package per task. Its near-term objective is breadth with an honest
minimum bar: an admitted, self-contained package that can reset in GenManip and
has explicit visual, tabletop, and provisional IK evidence.

It does not run policies, episodes, benchmark scoring, collision-free motion,
or liquid simulation.

## Queue Rule

A task enters the queue only when every required asset role has a source-bound
ConvertAsset package with `admission_status: pass`, the binding resolves through
Scenario Forge's normal source boundary, and a canonical task recipe exists.

Missing roles are emitted as one de-duplicated ConvertAsset admission request.
Scenario Forge neither substitutes semantically similar objects nor adds local
asset-specific physics patches. ConvertAsset may make an auditable producer-side
copy repair while retaining the immutable original source.

## Canonical Package and Versioning

Every Feishu row has one canonical package first. Background, asset package
revision, task recipe, and candidate-generation algorithm are all versioned
inputs. A background change compiles a new immutable package; it does not
silently alter prior evidence.

`latest` is an index, never an overwritten package. It is promoted automatically
only when all of these gates pass:

1. self-contained package closure;
2. GenManip load/reset;
3. robot-facing tabletop placement and edge margin;
4. automated visual review;
5. fixed-base provisional IK for every initial task-grasped object.

A retained candidate may show partial evidence while its missing gates remain
`not_run`; it cannot be promoted.

## Fixed-Base Provisional IK

Scenario Forge writes a deterministic `composed_bbox_top_down/v0.1` request under
the eBench adapter. It names each initially grasped object, assigned arm,
top-down anchor, and a 12 cm pregrasp offset, with robot base motion fixed to
zero. The request also gives four world-yaw candidates; the external runtime maps
the direction/yaw convention to the concrete end-effector frame for Lift2.
External GenManip/CuRobo returns the solver result; Scenario Forge verifies request
identity, per-object pass coverage, and zero base motion before retaining the evidence.

The result is intentionally `provisional_ik_pass`: it proves neither a
collision-free approach, grasp closure, lift, dual-arm coordination, interaction
success, liquid transfer, policy success, nor benchmark success.

## Product Surface

The factory writes a static task directory with queue state, immutable release
records, the newest retained candidate, `latest`, default background, and
blockers. A candidate exposes useful render/reset evidence but is visibly
separate from `latest`, so partial gates cannot be mistaken for qualification.
The directory can be deployed as a read-only page. It remains a view over
evidence rather than an authority that can override failed gates.

Each release may also declare a product tier, a score ceiling, and missing
capabilities. `canonical_candidate` means the package is intended to become the
canonical task once every promotion gate passes. `prototype` means the package
is useful for layout or integration work but is knowingly incomplete. The score
ceiling is a contract limit derived from the currently representable rubric; it
is not a measured benchmark score or policy success rate.

One task may have multiple immutable background variants. The directory groups
them under one task row, while every variant remains a separate self-contained
package with its own evidence. Background switching is therefore a compile-time
choice rather than a runtime USD variant that could invalidate previously
reviewed evidence.

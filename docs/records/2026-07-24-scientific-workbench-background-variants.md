# Scientific workbench background-variant evidence (2026-07-24)

Scenario Forge consumed the ConvertAsset batch admission
`outputs/scientific_environment_background_screening_20260723/convertasset_batch_admission.yaml`
and generated seven fixed-workspace variants under
`outputs/scientific_workbench_background_variants_20260724/`.

The generator accepted only `visual_static_environment` packages admitted for
Isaac 4.1. For every variant it kept the baseline eBench table asset and pose,
Lift2 spawn, conical-bottle and graduated-cylinder assets and poses, task
steps, invariants, and success contract. The scenario id is suffixed with the
candidate id for traceability.

The background-specific scene changes are the background `scene.asset_id`, its
visual-only instance pose, and—only for a reviewed replacement—the inactive
source-island paths. The generated `background_variants_manifest.json` records
the source hash and placement transform for each candidate, plus
fixed-workspace digests. Placement converts authored USD units and fits the
background's physical bounds to the reference room envelope; it does not
rewrite the producer package. The placement layer also folds each admitted source `/World`
root scale/translation into the destination instance transform, preventing
source-authored offsets from moving a room away from the eBench workspace. All
seven packages pass
`scenario_forge package check --require-asset-lock`.

The composition pass distinguishes structural rendering from visual acceptance.
`scientific_environment_084` maps the source `/World/group_078` wet-lab island
to the unchanged eBench tabletop and deactivates that complete 393-prim source
assembly in the composition layer. A clean-room pixel review passed its
overview and close-up: the table, dual-arm robot, graduated cylinder, and
conical flask are visible in a believable laboratory context, with no source
island visibly overlapping the task table.

`scientific_environment_059` maps and hides the complete
`/World/group_063` island assembly correctly but remains a visual pilot: its
overview is busy with nearby chairs, lights, and glare. `067` was withdrawn
after a render showed another source bench still crossing the workcell; `081`
was withdrawn because its flattened dense room has no credible island/aisle
insertion. `066`, `083`, and `085` remain envelope-centred structural variants
only. This avoids guessing individual anonymous meshes or moving the task
workspace.

Isaac Sim 4.1 / GenManip initial-scene rendering was run in a detached canary
workspace. Each successful evidence directory contains the close-up and
overview PNGs, a render manifest, and a structural `visual_ready_gate.yaml`.
The close-up intentionally hides the room for a stable desk-invariance check.
For anchored replacements the overview is now targeted from post-reset runtime
bounds of Lift2, the injected runtime table, and both vessels—not from a
compiler-stage tabletop coordinate. The evidence moment is post-reset,
pre-action and has zero actions.

`visual_ready_gate.yaml` is a structural gate, not a composition verdict. The
current visually approved delivery is `scientific_environment_084`; all other
candidates retain the claim boundaries described above. None of the evidence
is a policy, oracle, physics, or liquid-transfer result.

The ConvertAsset producer revision and source-bound claims remain authoritative.
Scenario Forge does not add background colliders, mass/inertia, MDL fallbacks,
or PhysX-warning suppression.

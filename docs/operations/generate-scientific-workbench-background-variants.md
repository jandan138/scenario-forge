# Generate fixed-workspace background variants

The July 23 screening/admission batch and July 26 workspace variants are now
cold-archived. Restore their exact directories before running the historical
commands below; current task heads do not require those batches.
See [round 2 archival](../records/2026-09-05-round2-build-input-decoupling.md).

Full-room packages emit the v0.3 seven-view preview contract described in
[`genmanip-full-room-preview-v0.3.md`](../design/genmanip-full-room-preview-v0.3.md).
Run it through the existing managed EOS/Isaac environment; do not create a
task-local Conda environment or patch GenManip. Ordinary tabletop packages
continue to use the v0.2 three-view contract.

This workflow answers one narrow question: can the scientific workbench task
keep the eBench table, Lift2 robot, two vessels, poses, and task contract fixed
while swapping only the visual laboratory background? The answer is yes, when
the replacement is an admitted ConvertAsset `visual_static_environment`
package with the eBench `/World` consumer-scope contract. An authored source
with a different or multi-root namespace must first receive a source-bound
ConvertAsset facade; Scenario Forge does not rename or merge USD roots.

For one complete external room that needs multiple independently selectable
workcells, use the v0.2 zone-profile workflow in
[`generate-external-room-zone-variants.md`](generate-external-room-zone-variants.md).
It keeps one immutable room asset and creates several packages keyed by
`variant_id`; it does not crop the USD or introduce a GenManip runtime switch.

## Inputs

Run from the Scenario Forge repository root with the existing EOS test
environment. The batch admission file and its seven package directories are
producer-owned deliveries; Scenario Forge validates and composes them but does
not repair USD, MDL, mesh, mass, or collider data.

```bash
TEST_ENV=/cpfs/shared/simulation/zhuzihou/dev/conda-managed/envs/embodied-eval-os-sim-newton-ebench-experimental-py310
PYTHONPATH=src "$TEST_ENV/bin/python" \
  scripts/generate_scientific_workbench_background_variants.py \
  --base-package "$PWD/outputs/scientific_workbench_bimanual_pour" \
  --admission "$PWD/outputs/scientific_environment_background_screening_20260723/convertasset_batch_admission.yaml" \
  --background-root "$PWD/outputs/scientific_environment_background_screening_20260723/packages" \
  --workspace-profiles "$PWD/outputs/scientific_workbench_workspace_profiles_20260724/workspace_profiles_manifest.json" \
  --out "$PWD/outputs/scientific_workbench_workspace_profiled_variants_20260726" \
  --spec "$PWD/examples/scientific_workbench/bimanual_pour/scenario.yaml"
```

The generator reads the existing baseline package sources, verifies each
candidate's source hash, scope, producer revision, manifest, and pass status,
then compiles one ordinary Scenario Forge package per background. It changes
`scene.asset_id`, the variant `scenario_id`, and the visual background
instance's `scene.pose` transform. For an unprofiled visual-only room, that
transform can fit the package bounds into the reference visual envelope. For a
workspace-profiled room, it preserves the producer-declared workcell metric;
otherwise the producer's eBench clearance would be rescaled and become false.
It never edits the producer USD. The table, robot, objects, their poses,
steps, invariants, and success predicate are compared against the baseline
before compilation.

The admission manifest also records the source `/World` root transform. Since
the compiled instance authors its own transform, the generator folds that
source scale/translation into the instance pose; otherwise a room whose source
root is scaled or translated can render tens of metres away. This remains an
instance-layer operation and does not change ConvertAsset's source package.

With `--workspace-profiles`, the batch does not fall back to putting a workcell
at an arbitrary room centre. It generates only candidates with either a
source-bound ConvertAsset replacement profile or a separately reviewed
built-in anchor. A profile anchor is expressed in the producer's
source-composed coordinate frame. Every `profiled` profile must therefore
declare an exact machine-readable mapping:

```yaml
coordinate_mapping:
  frame: source_composed
  source_composed_meters_per_unit: <exact positive number>
```

The admitted USD stage `metersPerUnit` is not a substitute: several source
laboratories use inherited metadata that does not equal their audited workcell
scale. Scenario Forge converts the profile anchor with this mapping and
preserves that scale rather than applying the generic visual-envelope fit.
Both raw and mapped values are recorded in the variant manifest. A profile
without this field is rejected before package generation.

## Workspace anchors and the source table

An anchored background is a source-bound replacement of one complete source
island: its reviewed tabletop point maps to the fixed eBench tabletop, and its
complete source assembly is made inactive in the composition layer. The eBench
table, robot, vessels, poses, and task are not moved or replaced; the rest of
the background room remains visible. This is the explicit answer to “will the
old background table disappear?”: it disappears only when its whole reviewed
source assembly is the one being replaced.

The current profile-enabled set is:

| Candidate | Source assembly | Current image-review status |
| --- | --- | --- |
| `scientific_environment_084` | `/World/group_078` | approved: the clear workcell overview is the current recommended delivery |
| `scientific_environment_059` | `/World/group_063` + `064` + `073` + `241` | mapping received; integrated render complete, visual QA pending |
| `scientific_environment_066` | `/World/group_111` | mapping received; integrated render complete, visual QA pending; old envelope-fit render remains rejected |
| `scientific_environment_067` | not applicable | profile-4 final disposition: no rule-compliant placement exists for the fixed 2.345 × 2.645 m eBench workbench; excluded before package generation |
| `scientific_environment_083` | `/World/group_025` + `026` + `027` | mapping received; a reviewed +90° visual composition yaw and authored-camera-direction retarget now produce a passing combined overview; optional floor-drain prims remain active by default |

`067`, `081`, and `085` are explicit `not_applicable` results. `067` has no
rule-compliant placement for the fixed eBench footprint; `081` needs anonymous
loose-mesh masks around dense bench rows; and `085` has no island large enough
for the fixed footprint. They are excluded from the profile-enabled output
rather than silently becoming envelope-centred variants.

The anchor is recorded in `background_variants_manifest.json` under
`background_placement.workspace_anchor`, while `workspace_integration` records
the ConvertAsset profile path, provenance, source-composed anchor, converted
physical anchor, mandatory roots, and optional paths. Adding another anchor
requires both a source-prim/clearance review and a post-reset image review; do
not infer one from an arbitrary mesh.

## Outputs

The generated root is Git-ignored because it contains the complete source
closures needed by GenManip. The current workspace-profile mapping sidecar is
consumed; it contains these four integrated packages:

```text
outputs/scientific_workbench_workspace_profiled_variants_20260726/
  scientific_environment_059/
  scientific_environment_066/
  scientific_environment_083/
  scientific_environment_084/
  background_variants_manifest.json
```

The manifest explicitly lists `081` and `085` under
`excluded_workspace_candidates` with the producer-provided reason.

Each package has a normal `manifest.yaml`, `locks/asset_lock.yaml`, and
`adapters/ebench/genmanip/` export. Validate every package before handing it
off:

```bash
for package in outputs/scientific_workbench_workspace_profiled_variants_20260726/scientific_environment_*; do
  PYTHONPATH=src "$TEST_ENV/bin/python" -m scenario_forge.cli \
    package check "$package" --require-asset-lock
done
```

## Rendering evidence

The GenManip adapter's three evidence views are written below each collected
package after an Isaac Sim 4.1 run:

```text
<package>/adapters/ebench/genmanip/evidence/initial_scene/
  workspace_closeup.png
  scene_overview.png
  task_object_closeup.png
  render_manifest.json
  visual_ready_gate.yaml
```

`workspace_closeup.png` checks the unchanged tabletop workspace. For this
evidence-only view the renderer temporarily hides the visual-static room, so a
room wall or floor cannot mask the fixed table, robot, or vessels. It is not
proof that the task has been embedded well in the room.
`task_object_closeup.png` uses the task-object bounds without the robot or table
as camera anchors. It is the material and support-contact inspection view, not
task-success evidence.
`scene_overview.png` restores the room but, for an anchored replacement,
centres its temporary evidence camera at the fixed eBench workspace. When the
admitted package carries a source Perspective camera, Scenario Forge preserves
that camera's direction and retargets it to the unchanged workspace; this
avoids aiming at a source-only wall or object. Candidate `083` additionally
uses a reviewed +90° instance-layer yaw around its source anchor so the room
row sits behind the workcell. Candidate `067` is profile-4 `not_applicable`:
the producer's measured room geometry has no rule-compliant placement for the
fixed eBench workcell, so the generator excludes it before rendering. These are
composition-layer choices only: the source USD, table, robot, task objects, and
dynamic semantics are unchanged.

The visibility override and camera provenance are recorded in
`render_manifest.json` and `render_request.yaml`; neither changes the packaged
scene or policy camera. These are post-reset, pre-action views; they do not run
an oracle, policy, pouring motion, or liquid-transfer metric.

Use a private, detached GenManip canary checkout for rendering. Do not copy the
package into the shared `GenManip/saved/assets` tree, and do not modify the
GenManip checkout. The renderer may report source-scene USD UV-index warnings
or the known Lift2 dummy-base PhysX warnings; those are distinct from the
ConvertAsset material-blocking signals and are recorded in the renderer log.

## Claim boundary

After a profile mapping passes preflight and the corresponding GenManip image
passes visual review, the variant proves package-level background substitution
with a fixed eBench workspace and valid package/asset locks. A
`visual_ready_gate.yaml` proves only that Isaac/GenManip constructed the scene
and required runtime prims existed; it is not composition acceptance. The
ConvertAsset source-side comparison images prove profile coverage, not final
eBench framing or visual quality. `084` and the retaken `083` are the visually
accepted integrated deliveries in the current clean-room review. The old `067`
profile-3 package is retained only as a historical structural/closeup
diagnostic; profile-4 excludes 067 from current generation. The old 066
post-reset render is retained as a rejected diagnostic:
it used the package-stage `metersPerUnit`, compressed the audited clearance,
and showed the room shell over the workcell.

None of these artifacts prove that a background is dynamically interactable,
that the table or room has calibrated physics, that an arm can grasp either
vessel, or that the five-step bimanual pour succeeds. The admitted backgrounds
are visual-static only. If a background is later needed as an interactive
object, it must receive a new ConvertAsset dynamic admission and a separate
task-specific validation.

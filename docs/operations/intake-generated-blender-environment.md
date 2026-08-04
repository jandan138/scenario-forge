# Intake a Generated Blender Environment

This workflow turns one Code-as-Room source delivery into selectable visual
backgrounds for an ordinary eBench task package. Scenario Forge remains the
portable compiler: it does not run Blender, rewrite USD/MDL, or add background
physics.

## Ownership

- Code-as-Room owns `room.blend`, the Z-up metric `room_source.usdc`, relative
  textures, semantic Zone roots, source evidence, `source_manifest.json`, and
  the hash-bound `support_relations.json` inventory for non-floor decorations.
- ConvertAsset owns the `/World` consumer facade, dependency closure, Isaac
  4.1 admission, an independent geometry audit of every declared support
  relation, and source-bound workspace-zone clearance profiles.
- Scenario Forge verifies both handoffs, preserves the fixed eBench
  table/robot/task objects, and compiles one package per eligible Zone.

The room is always a `visual_static_environment`. Its furniture is visual
context, not task-interactive rigid-body geometry.

## 1. Intake the source delivery

```bash
PYTHONPATH=src python scripts/intake_generated_environment.py \
  --asset-id scientific_environment_code_room_example4_v1 \
  --delivery-root "$CODE_AS_ROOM_DELIVERY" \
  --out "$OUTPUT_ROOT/intake.yaml"
```

For `room-source-v2`, the intake additionally requires a passing engineering
review, verifies that `support_relations.json` is part of the declared closure,
and binds it to the exact `room_source.usdc` hash. It emits no absolute source
path. Files that are present but absent from the producer manifest are reported
as warnings.

## 2. ConvertAsset admission and Zone profiling

Build a source-bound facade that mounts `/Room` directly at `/World`, then
normalize it with:

```text
asset_role: visual_static_environment
source_runtime: blender44
target_runtime: isaac41
target_benchmark: scenario-forge
asset_scope_prim: /World
gates: static,runtime
```

The r2 producer delivery explicitly authors the square HDR as `latlong`; the
facade therefore needs no light-format repair. The facade builder still accepts
an explicit legacy DomeLight override for older immutable sources.

Run `profile-room-zones` from ConvertAsset with a pinned raw source hash, a
separate facade geometry hash, and complete Zone assembly roots. It supports:

- `open_floor`: place the workcell in audited free floor space and remove
  nothing;
- `replace_assembly`: deactivate only complete producer Zone roots after their
  2.345 × 2.645 × 2.2 m clearance passes.

Do not list anonymous meshes as ad-hoc masks.

Generated-room admission must also include the support sidecar. ConvertAsset
recomputes each footprint/contact relation from the composed raw USD and writes
`evidence/support_audit/report.json`. A workspace-zone request must point to
that passing report, so removing a support parent also carries its reviewed
dependent-object closure.

## 3. Compile and render eBench packages

```bash
export ISAAC_ENV=/cpfs/shared/simulation/zhuzihou/dev/conda-managed/envs/embodied-eval-os-sim-isaacsim41-genmanip-py310
export CUROBO_SRC=/cpfs/shared/simulation/mamengchen/curobo-wbc-backup/src
export PATH="$ISAAC_ENV/bin:$PATH"
export PYTHONPATH="$PWD/src:$CUROBO_SRC"
export LD_LIBRARY_PATH="/isaac-sim/exts/omni.isaac.ml_archive/pip_prebundle/nvidia/cuda_runtime/lib:$ISAAC_ENV/lib/python3.10/site-packages/torch/lib:${LD_LIBRARY_PATH:-}"

python scripts/generate_scientific_workbench_background_variants.py \
  --base-package outputs/scientific_workbench_bimanual_pour \
  --admission "$OUTPUT_ROOT/scenario_forge_consumer_admission.yaml" \
  --background-root "$OUTPUT_ROOT" \
  --generated-environment-intake "$OUTPUT_ROOT/intake.yaml" \
  --workspace-zone-profiles \
    "$OUTPUT_ROOT/workspace_profiles/workspace_zone_profiles_manifest.json" \
  --background-asset-id scientific_environment_code_room_example4_v1 \
  --out outputs/scientific_workbench_code_room_example4_zone_variants \
  --render \
  --isaac-python "$ISAAC_ENV/bin/python" \
  --genmanip-root "$GENMANIP_CANARY"
```

The generator preserves the package's table, Lift2, vessels, steps, and metric.
It changes only the visual background asset, reviewed room instance pose,
reviewed Zone inactivation, and variant scenario ID.

Scenario Forge refuses a generated background when the intake certificate is
missing, the ConvertAsset certificate is missing or blocked, or their raw
source hash/relation/removal counts disagree. Previously published images must
be quarantined until a new source revision passes this chain and is re-rendered.

## Acceptance

For every variant, review:

- `evidence/initial_scene/scene_overview.png`;
- `evidence/initial_scene/workspace_closeup.png`;
- `evidence/initial_scene/visual_ready_gate.yaml`.

Then run `package check --require-asset-lock`. A passing preview establishes
only the post-reset, pre-action composition. It does not establish grasp,
pouring, policy, or liquid-transfer success.

# Generate the Bimanual Pour Package

The golden task uses the scientific-workbench scenario spec, a closed USD scene
bundle, and the EBench Lift2 profile.

The canonical scenario is task-ready rather than a raw full-context import. Its
USD overlay deactivates unrelated loose objects and all but one articulated
appliance subtree while leaving `lab_001.usd` untouched. `DryingBox_03` remains as
the single visible laboratory-context device. Its portable USD composition uses
the source-bound ConvertAsset physics package rather than unqualified raw-source
physics. Current GenManip initialization then removes colliders recursively below
the `room` prim, so in that adapter runtime DB03 must be treated as visible context,
not as a collision-active appliance.

The golden spec uses `scenario-spec/v0.2` `scene.overlay_asset_ids`. Entries are
ordered strongest to weakest, followed by the base environment; every overlay must
have the same `/World` root as the base. Scenario Forge's task layer is stronger
than both, so its scene pose and inactive-prim curation still win. The configured
`manip/lift2/R5a` dual-arm robot and GenManip injection path are unchanged.

The checked EOS environments can be reused directly; this workflow does not require
creating or modifying a conda environment. In the current shared deployment:

```bash
TEST_ENV=/cpfs/shared/simulation/zhuzihou/dev/conda-managed/envs/embodied-eval-os-sim-newton-ebench-experimental-py310
ISAAC_ENV=/cpfs/shared/simulation/zhuzihou/dev/conda-managed/envs/embodied-eval-os-sim-isaacsim41-genmanip-py310
LABUTOPIA_ROOT=/cpfs/shared/simulation/zhuzihou/dev/LabUtopia
GENMANIP_SOURCE=/cpfs/shared/simulation/zhuzihou/dev/GenManip
CUROBO_SRC=/cpfs/shared/simulation/mamengchen/curobo-wbc-backup/src
CONVERT_ASSET_ROOT=/cpfs/user/zhuzihou/dev/ConvertAsset
CONVERT_ASSET_DELIVERY="$CONVERT_ASSET_ROOT/docs/records/evidence/2026-07-14-aan-dryingbox-dynamic-physics-profile"
CONVERT_ASSET_REVISION=324ce6e6d4395ccfda1e59e5ae89de9389cdf225

export PYTHONPATH="$PWD/src:$CUROBO_SRC"
export LD_LIBRARY_PATH="/isaac-sim/exts/omni.isaac.ml_archive/pip_prebundle/nvidia/cuda_runtime/lib:$ISAAC_ENV/lib/python3.10/site-packages/torch/lib:${LD_LIBRARY_PATH:-}"
export ACCEPT_EULA=Y OMNI_KIT_ACCEPT_EULA=YES PYTHONNOUSERSITE=1

"$TEST_ENV/bin/python" scripts/generate_scientific_workbench_bimanual_pour.py \
  --source-usd "$LABUTOPIA_ROOT/outputs/usd_asset_packages/lab_001_localized_20260707/lab_001.usd" \
  --source-uri "LabUtopia:lab_001_localized_20260707" \
  --convert-asset-package "$CONVERT_ASSET_DELIVERY/package" \
  --convert-asset-manifest "$CONVERT_ASSET_DELIVERY/manifest.json" \
  --convert-asset-revision "$CONVERT_ASSET_REVISION" \
  --out outputs/scientific_workbench_bimanual_pour \
  --isaac-python "$ISAAC_ENV/bin/python" \
  --genmanip-root "$GENMANIP_SOURCE"
```

The inbound adapter requires the delivery manifest to match the package's embedded
manifest, binds it to the exact `lab_001.usd` source hash, and validates the
declared `/World/DryingBox_03` scope, profile hash, Isaac 4.1 runtime gates, and
zero scoped PhysX mass/inertia warning count. It then maps the package into the
generic asset contract; it does not add a Scenario Forge mass/inertia/center-of-mass
fix or any warning suppressor. The copied runtime closure retains `deps/`,
`physics/`, and `overlays/` while excluding upstream `evidence/`.

When ConvertAsset replaces the provisional-geometry profile with measured
parameters, point these package and manifest arguments (and their producer revision
provenance) at the new delivery. Do not edit the scenario to author local physics,
and do not modify the original LabUtopia USD.

The command replaces the managed output directory deterministically and produces:

- the portable package at `outputs/scientific_workbench_bimanual_pour`;
- a GenManip collected package below
  `outputs/scientific_workbench_bimanual_pour/adapters/ebench/genmanip`.
- an embedded, transport-only Scenario Forge runtime contract under the episode
  metadata `task_data`, carrying runtime object IDs, state prim paths, named
  frames, actor bindings, steps, invariants, and success semantics;
- a post-reset, pre-action tabletop close-up and scene overview below
  `adapters/ebench/genmanip/evidence/initial_scene/`, with their render manifest,
  runtime log, hashes, and visual-ready gate.

`outputs/` is intentionally Git-ignored, and this package is marked
non-redistributable until its dependency distribution policy is fully cleared. The
rendered images and package remain local build artifacts and must not be committed;
a fresh clone must run the command above to recreate them. Only compact hashes and
bounded review/runtime records are committed.

Rendering is strict by default: a renderer failure, timeout, missing/stale image,
source-bundle or request mismatch, runtime-log or image hash mismatch, missing
required runtime prim, or declared known blocking material signal rejects the
build. Validation always compares the request with inputs freshly derived from the
current package. For a static-only inspection that intentionally provides no visual
evidence, add `--static-only` and omit the Isaac/GenManip arguments.

## Generic static compiler

The task-specific script above remains the default path when current Isaac preview
evidence is required. Its static compile and GenManip export stages can also be
run through the generic compiler after writing a local
`scenario-source-bindings/v0.1` file for the base scene and ConvertAsset delivery:

```bash
scenario-forge package compile \
  --spec examples/scientific_workbench/bimanual_pour/scenario.yaml \
  --source-bindings /path/to/scenario_source_bindings.yaml \
  --out outputs/scientific_workbench_bimanual_pour \
  --export-genmanip
```

The bindings file contains `source_usd`, `package_dir`, and `manifest_path` local
paths. The ScenarioSpec continues to contain only asset IDs and portable task
intent. This command performs no preview render and no oracle rollout; use the
task-specific script for the former and EOS/GenManip for the latter. See
[Scenario Source Bindings](../design/scenario-source-bindings.md) for the complete
binding shape.

The embedded runtime contract is data transport, not a success result. Current
GenManip does not automatically pass it into the metrics manager, and the selected
vessels still fail the rigid-root identity preflight. Do not label a package
frame-metric-ready until those assets, an explicit frame predicate, and the
downstream metric capability are all present.

Do not install the package below `$GENMANIP_SOURCE/saved/assets`. In the shared
deployment that path is a symlink into the shared EBench asset directory, so a
seemingly local overwrite would mutate shared data. Stage runtime inputs in a new
private workspace instead. The following example exports the clean GenManip `HEAD`,
links the base-asset directories for read-only use, and copies this package into a
real private `collected_packages` directory:

```bash
PACKAGE_ID=scientific_workbench_bimanual_pour
COLLECTED="$PWD/outputs/scientific_workbench_bimanual_pour/adapters/ebench/genmanip"
CANARY_ROOT="${TMPDIR:-/tmp}/scenario-forge-genmanip-canary-$(date -u +%Y%m%dT%H%M%SZ)"
BASE_ASSETS="$(readlink -f "$GENMANIP_SOURCE/saved/assets")"

test ! -e "$CANARY_ROOT"
mkdir -p "$CANARY_ROOT"
git -C "$GENMANIP_SOURCE" archive HEAD | tar -x -C "$CANARY_ROOT"
mkdir -p "$CANARY_ROOT/saved/assets/collected_packages"
for name in mesh_data miscs object_usds robot_usds scene_usds; do
  ln -s "$BASE_ASSETS/$name" "$CANARY_ROOT/saved/assets/$name"
done

target="$CANARY_ROOT/saved/assets/collected_packages/$PACKAGE_ID"
test ! -e "$target"
cp -a "$COLLECTED" "$target"
test "$(realpath "$target")" = "$target"
diff -qr "$COLLECTED" "$target"
```

Then submit the collected-package ID `scientific_workbench_bimanual_pour` through
the normal GenManip evaluation entry point with `CANARY_ROOT` as its workspace. The
runtime must already provide the `manip/lift2/R5a` robot, its robot assets, and its
planner configuration. Never replace or delete an existing target during a Canary;
use a new workspace and run ID. Keep Ray's temporary root short (for example,
`/tmp/sf-ray-<timestamp>`); Unix-domain socket paths have a platform length limit.

## What this verifies

Static package generation verifies the asset copy, USD composition, object UID
mapping, material rebinding, task config, episode metadata, registered proxy
metrics, and package contracts. The default render additionally verifies that
GenManip can initialize/reset the scene and produce current evidence for both QA
views without taking an action. Neither check establishes policy success, task
success, physics fidelity, or real liquid transfer.

The source data is non-commercial and includes third-party dependencies. Generated
packages are marked non-redistributable until every bundled dependency has a cleared
distribution policy.

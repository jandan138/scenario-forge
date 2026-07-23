# Generate the Scene1_hard Bimanual Pour Package

This task puts the paper's complete `Scene1_hard.usd` laboratory behind the
unchanged EBench Lift2 dual-arm pouring workspace. It deliberately uses three
separate producer-owned inputs:

| Layer | Exact source | Package role |
| --- | --- | --- |
| Complete visual room | `Scene1_hard.usd:/World/lab_015` | ConvertAsset `visual_static_environment` |
| EBench worktable | `lab_001.usd:/World/table` | ConvertAsset `visual_static_object` |
| Flask and cylinder | existing `lab_001` source-bound packages | dynamic manipulation objects |

`/World/lab_015` is the one complete room payload under `Scene1_hard.usd`.
ConvertAsset must extract that exact parent-layer scope: it retains the paper
scene's meters-per-unit, rotation, translation, and scale while excluding Clean
Beaker's root-level beakers, buttons, and task markers. Directly normalizing
`SubUSDs/lab_015.usd` is not valid: without its parent composition context the
same geometry evaluates at roughly 8 mm × 22 mm × 4 mm instead of roughly 8 m ×
22 m × 4 m.

The table intentionally comes from the existing EBench-compatible `lab_001`
source, not `Scene1_hard:/World/table_hard`. The current main Scene1 table has
five unresolved material dependencies, and the historical source revision that
claimed to repair it cannot be materialized here because its Git LFS object is
404. That is an upstream asset-delivery problem, not a reason to add local
textures, MDL fallbacks, or table-specific physics in Scenario Forge.

Both visual-static packages must have zero package-authored rigid bodies,
colliders, joints, or articulations. GenManip's ordinary table layout remains
responsible for its generic support collider (`add_colliders: true`,
`add_rigid_body: false`). Scenario Forge does not author mass, inertia, colliders,
PhysX-warning suppression, or material repairs for these inputs.

The collected scene intentionally does not pre-instantiate this visual-static
table. Its episode layout instead points to
`source_bundle/scenario_forge_runtime/table.usd`, a thin adapter composition layer
that loads the complete table package for material closure while preserving the
existing EBench episode pose and scale. This is what lets unmodified GenManip
recovery execute its native static-table collider path.

## Locked producer delivery

ConvertAsset `main@73a84d3c2cfc8378cd5c255cf2282a20da017b8f`
closed both producer blockers and delivered the exact source-bound packages used
by this runbook:

| Input | Package | Manifest |
| --- | --- | --- |
| Scene1 room | `outputs/convertasset-scene1-hard-lab015-room-20260723` | `evidence/manifest.json` |
| EBench table | `outputs/convertasset-lab001-table-visual-static-20260723` | `evidence/manifest.json` |

Both manifests have `overall_status: pass`, seven passing stage gates, no blocked
reasons, no active physics residue, and zero scoped or unattributed PhysX warning
events. The visual-static reset subgate is correctly `not_applicable` for the
empty rigid-body set while the scope reset still passes. Dependency admission is
scope-first: unresolved `table_hard` dependencies remain recorded as out of scope
and are not part of either consumer claim.

Do not rerun ConvertAsset from this workflow or reconstruct an external manifest.
The package's own `evidence/manifest.json` is the delivered manifest consumed
below.

## Build inputs and isolated runtime

Use the checked EOS environments directly; this workflow neither creates nor
modifies a conda environment. Run from the Scenario Forge repository root.

```bash
TEST_ENV=/cpfs/shared/simulation/zhuzihou/dev/conda-managed/envs/embodied-eval-os-sim-newton-ebench-experimental-py310
ISAAC_ENV=/cpfs/shared/simulation/zhuzihou/dev/conda-managed/envs/embodied-eval-os-sim-isaacsim41-genmanip-py310
LABUTOPIA_ROOT=/cpfs/shared/simulation/zhuzihou/dev/LabUtopia
GENMANIP_SOURCE=/cpfs/shared/simulation/zhuzihou/dev/GenManip
CUROBO_SRC=/cpfs/shared/simulation/mamengchen/curobo-wbc-backup/src
CONVERT_ASSET_ROOT=/cpfs/user/zhuzihou/dev/ConvertAsset

CONVERT_ASSET_REVISION=73a84d3c2cfc8378cd5c255cf2282a20da017b8f
SOURCE_VESSEL_REVISION=ba4ac8ccbf3c32f257abdbb68a554a74a90003f1
TARGET_VESSEL_REVISION=4bb541161a652cc4e5dd63253adffba018f17137
GENMANIP_REVISION=014bf5435a373df9b3bcf5a69aa7fe22d17f613d

SCENE1_HARD_ROOT="$LABUTOPIA_ROOT/assets/chemistry_lab/hard_task/Scene1_hard.usd"
SCENE1_ENVIRONMENT_SOURCE="$SCENE1_HARD_ROOT"
SCENE1_ENVIRONMENT_SCOPE=/World/lab_015
TABLE_SOURCE="$LABUTOPIA_ROOT/outputs/usd_asset_packages/lab_001_localized_20260707/lab_001.usd"
VESSEL_SOURCE="$TABLE_SOURCE"
SOURCE_VESSEL_DELIVERY="$CONVERT_ASSET_ROOT/docs/records/evidence/2026-07-14-aan-labutopia-vessel-interaction-profile/conical_bottle03"
TARGET_VESSEL_DELIVERY="$CONVERT_ASSET_ROOT/docs/records/evidence/2026-07-15-aan-graduated-cylinder-r3-grasp-section/graduated_cylinder_03"
SCENE1_ENVIRONMENT_PACKAGE="$PWD/outputs/convertasset-scene1-hard-lab015-room-20260723"
SCENE1_ENVIRONMENT_MANIFEST="$SCENE1_ENVIRONMENT_PACKAGE/evidence/manifest.json"
TABLE_PACKAGE="$PWD/outputs/convertasset-lab001-table-visual-static-20260723"
TABLE_MANIFEST="$TABLE_PACKAGE/evidence/manifest.json"

RUN_ID="$(date -u +%Y%m%dT%H%M%SZ)"
CANONICAL="$PWD/outputs/scientific_workbench_bimanual_pour"
CANDIDATE="$PWD/outputs/.scientific_workbench_bimanual_pour.candidate-$RUN_ID"
BACKUP="$PWD/outputs/.scientific_workbench_bimanual_pour.backup-$RUN_ID"
CANARY_ROOT="${TMPDIR:-/tmp}/scenario-forge-genmanip-canary-$RUN_ID"
BASE_ASSETS="$(readlink -f "$GENMANIP_SOURCE/saved/assets")"

test -f "$SCENE1_HARD_ROOT"
test -f "$SCENE1_ENVIRONMENT_SOURCE"
test -f "$TABLE_SOURCE"
test -f "$SCENE1_ENVIRONMENT_PACKAGE/asset.usd"
test -f "$SCENE1_ENVIRONMENT_MANIFEST"
test -f "$TABLE_PACKAGE/asset.usd"
test -f "$TABLE_MANIFEST"
test ! -e "$CANDIDATE"
test ! -e "$BACKUP"
test ! -e "$CANARY_ROOT"
git clone --no-hardlinks "$GENMANIP_SOURCE" "$CANARY_ROOT"
git -C "$CANARY_ROOT" checkout --detach "$GENMANIP_REVISION"
test -z "$(git -C "$CANARY_ROOT" status --porcelain)"
mkdir -p "$CANARY_ROOT/saved/assets"
for name in mesh_data miscs object_usds robot_usds scene_usds; do
  ln -s "$BASE_ASSETS/$name" "$CANARY_ROOT/saved/assets/$name"
done

RUNTIME_STATE="$CANARY_ROOT/.scenario-forge-runtime"
mkdir -p "$RUNTIME_STATE/home" "$RUNTIME_STATE/cache" "$RUNTIME_STATE/tmp" \
  "$RUNTIME_STATE/pycache"
export PYTHONPATH="$PWD/src:$CUROBO_SRC"
export LD_LIBRARY_PATH="/isaac-sim/exts/omni.isaac.ml_archive/pip_prebundle/nvidia/cuda_runtime/lib:$ISAAC_ENV/lib/python3.10/site-packages/torch/lib:${LD_LIBRARY_PATH:-}"
export ACCEPT_EULA=Y OMNI_KIT_ACCEPT_EULA=YES PYTHONNOUSERSITE=1
export HOME="$RUNTIME_STATE/home"
export XDG_CACHE_HOME="$RUNTIME_STATE/cache"
export TMPDIR="$RUNTIME_STATE/tmp"
export PYTHONPYCACHEPREFIX="$RUNTIME_STATE/pycache"
```

The canary uses the shared EBench asset directory read-only through links. It
never installs anything there.

## Verify the source-bound deliveries

The generator performs the strict handoff validation. It checks the source hash,
exact scope, runtime and consumer profiles, visual-preservation fingerprint,
physical frame, zero-physics admission, runtime gates, warning counts, and package
closure before copying either asset.

## Compile, render, and validate

```bash
"$TEST_ENV/bin/python" scripts/generate_scientific_workbench_bimanual_pour.py \
  --scene1-source-usd "$SCENE1_ENVIRONMENT_SOURCE" \
  --table-source-usd "$TABLE_SOURCE" \
  --vessel-source-usd "$VESSEL_SOURCE" \
  --scene1-environment-package "$SCENE1_ENVIRONMENT_PACKAGE" \
  --scene1-environment-manifest "$SCENE1_ENVIRONMENT_MANIFEST" \
  --table-package "$TABLE_PACKAGE" \
  --table-manifest "$TABLE_MANIFEST" \
  --source-vessel-package "$SOURCE_VESSEL_DELIVERY/package" \
  --source-vessel-manifest "$SOURCE_VESSEL_DELIVERY/manifest.json" \
  --target-vessel-package "$TARGET_VESSEL_DELIVERY/package" \
  --target-vessel-manifest "$TARGET_VESSEL_DELIVERY/manifest.json" \
  --scene1-environment-revision "$CONVERT_ASSET_REVISION" \
  --table-revision "$CONVERT_ASSET_REVISION" \
  --source-vessel-revision "$SOURCE_VESSEL_REVISION" \
  --target-vessel-revision "$TARGET_VESSEL_REVISION" \
  --out "$CANDIDATE" \
  --isaac-python "$ISAAC_ENV/bin/python" \
  --genmanip-root "$CANARY_ROOT"

PYTHONPATH=src "$TEST_ENV/bin/python" -m scenario_forge.cli \
  package check "$CANDIDATE" --require-asset-lock
"$TEST_ENV/bin/python" -c \
  'import sys; from scenario_forge.adapters.ebench.preview import validate_genmanip_preview_evidence; validate_genmanip_preview_evidence(sys.argv[1])' \
  "$CANDIDATE/adapters/ebench/genmanip"
```

The renderer writes two post-reset, pre-action images:

- `workspace_closeup.png`: two vessels, both Lift2 end effectors, and work surface.
- `scene_overview.png`: complete Scene1 room, robot, EBench table, and vessels.

They verify scene composition only. They do not establish an oracle rollout,
grasp success, full physics fidelity, policy success, or liquid transfer. Reject a
candidate with missing/pink materials, an empty room, or a table/robot visibly
outside the laboratory.

## Promotion and runtime handoff

`outputs/` is Git-ignored. Do not install the candidate below
`$GENMANIP_SOURCE/saved/assets`: that path is a link into the shared EBench asset
directory. Copy a promoted package only into the private `CANARY_ROOT` workspace.

```bash
test -d "$CANONICAL"
test -d "$CANDIDATE"
test ! -e "$BACKUP"
mv "$CANONICAL" "$BACKUP"
if ! mv "$CANDIDATE" "$CANONICAL"; then
  mv "$BACKUP" "$CANONICAL"
  exit 1
fi
if ! PYTHONPATH=src "$TEST_ENV/bin/python" -m scenario_forge.cli \
  package check "$CANONICAL" --require-asset-lock; then
  mv "$CANONICAL" "${CANDIDATE}.failed-after-promotion"
  mv "$BACKUP" "$CANONICAL"
  exit 1
fi

PACKAGE_ID=scientific_workbench_bimanual_pour
COLLECTED="$CANONICAL/adapters/ebench/genmanip"
mkdir -p "$CANARY_ROOT/saved/assets/collected_packages"
target="$CANARY_ROOT/saved/assets/collected_packages/$PACKAGE_ID"
test ! -e "$target"
cp -a "$COLLECTED" "$target"
test "$(realpath "$target")" = "$target"
diff -qr "$COLLECTED" "$target"
```

The generated package remains non-redistributable until every bundled dependency
has a cleared distribution policy. Replace a producer input only with a new
passing package, manifest, and producer revision.

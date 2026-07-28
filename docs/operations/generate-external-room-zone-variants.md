# Generate External-Room Zone Variants

This operation turns one admitted, complete visual-static room into several
independently selectable eBench task packages. A zone is not a cropped USD:
each generated package keeps the complete room and places the fixed eBench
workcell at one reviewed source work area.

The first consumer is the current scientific-workbench bimanual-pour task.
The table, Lift2 robot, vessels, task steps, and success predicate remain
unchanged for every zone.

## 1. Freeze the external source snapshot

The delivered `3FO4K5C9JD44.rar` must first be extracted with an approved
RAR5-capable extractor. Keep the entire top-level directory together; the
entrypoint is `world.usda` and its `Assets/`, HDR, textures, and USDA/USD
sidecars are part of the source closure. The current restricted snapshot has
been extracted and hash-bound; rerun this step only when receiving a new
archive revision.

Do not put the archive, extracted source tree, or signed download URL in Git.
The supplied archive digest is:

```text
396608472548b545ffe1cf0c4d403a125590ac7398b669d1a6cd3436a6972e25
```

After extraction, create the restricted intake record. The source root below
is an example staging path, not a package runtime dependency.

```bash
PYTHONPATH=src python scripts/intake_external_environment.py \
  --asset-id scientific_environment_3fo4k5c9jd44 \
  --source-root "$PWD/outputs/external_environment_3fo4k5c9jd44/source/3FO4K5C9JD44" \
  --source-usd world.usda \
  --archive-sha256 396608472548b545ffe1cf0c4d403a125590ac7398b669d1a6cd3436a6972e25 \
  --restricted-provenance-id restricted/external-room/3FO4K5C9JD44 \
  --out "$PWD/outputs/external_environment_3fo4k5c9jd44/intake.yaml"
```

The intake declares `LicenseRef-Internal-Restricted` and
`redistributable: false`. It deliberately records no absolute source path or
credential-bearing URL.

## 2. ConvertAsset handoff

Give ConvertAsset the immutable extracted tree through the restricted channel
and the generated intake YAML. The raw source is a multi-root stage: its
default prim `/world` contains Looks/ground data, while room geometry and
lighting are under `/Root` and bind materials by absolute `/world/Looks/...`
paths.
Do **not** admit raw `/world` alone: that would produce an almost empty room.

Request one source-bound *consolidated consumer facade* without modifying the
raw source tree:

```text
background_asset_id: scientific_environment_3fo4k5c9jd44
source_usd: <staged-tree>/world.usda
raw_source_default_prim: /world
raw_source_visual_namespaces: [/world, /Root, /Render]
consumer_facade_default_prim: World
consumer_facade_scope: /World
asset_role: visual_static_environment
consumer_profile: scenario-forge
runtime_profile: isaac41
```

The exact machine-readable handoff is
[`external-room-facade-admission-request.yaml`](external-room-facade-admission-request.yaml).

The facade must retain the full room geometry, `/world/Looks` material
resolution, HDR/light closure, and render settings. Its manifest must expose
`entrypoints.default_prim: World`, `asset_entry_prim: /World`, and exactly
`asset_scope_prims: [/World]`; it must also record the raw-root-to-facade
mapping as source provenance. Its
`visual_preservation_fingerprint.package_after_role.scope_world_transforms`
must include the facade `/World` transform; Scenario Forge uses that
**package-side** transform for instance placement and never treats a raw
`/world` transform as the facade transform. Scenario Forge keeps its fixed
eBench scene root at `/World`, so a raw `/world` package is intentionally
rejected.

ConvertAsset owns this facade, dependency/material closure, source preservation,
and Isaac 4.1 runtime admission. Scenario Forge must not patch USD, textures,
MDL, collision, rigid-body, mass, inertia, or PhysX warnings locally.

### Delivered facade (2026-07-27)

ConvertAsset delivered the source-bound package at
`outputs/external_environment_3fo4k5c9jd44/package/`. It passed all seven
gates, exposes `/World`, and has 1,223 package-local dependencies with no
remote or missing dependency. Its bindings are intentionally two-stage:

- raw immutable `world.usda` SHA-256:
  `03aa64f29a20517e33e47c75620cd4326f70e39963b8880750a36f6988de45bd`;
- producer-owned facade SHA-256:
  `48770c5be9100266336663b67a7554455218f4ee24df5d5e33dbb96f672d5503`;
- package `asset.usd` SHA-256:
  `490899a591eff2faa55282603a9bd15a070a90dc727aae24420775d382d64776`.

The consumer admission binds restricted intake and zone profiles to the raw
source, then verifies separately through `evidence/facade_provenance.json`
that the ConvertAsset package came from the facade. Do not substitute one hash
for the other. The canonical asset identity is
`scientific_environment_3fo4k5c9jd44` (`o` is the letter O); an earlier
delivery sentence spelling `3f04...` used a zero and is not a valid ID.

Alongside the passing package and `evidence/manifest.json`, request a v0.2
zone-profile manifest. Its shape is:

```yaml
schema_version: scenario-forge-convertasset-workspace-zone-profile-manifest/v0.2
background_asset_id: scientific_environment_3fo4k5c9jd44
zones:
  north_bench_pair_east:
    status: profiled
    profile: scientific_environment_3fo4k5c9jd44__north_bench_pair_east_workspace_zone.yaml
```

Each referenced profile binds its source SHA and the **consumer-facade**
`/World` scope, then records a zone-specific source-composed anchor, coordinate
scale, clearance AABB, complete replaceable assembly roots, optional inactive
paths, and reviewed yaw. For a non-zero v0.2 `yaw.reviewed_yaw_deg`, the
profile must also declare
`yaw.rotation_convention: usd_z_up_right_handed_ccw`; Scenario Forge quarantines
an ambiguous non-zero yaw rather than guessing its sign. A `not_applicable`
result, or a consumer quarantine, excludes only that zone, not the complete
room.

The delivered profile revision v0.3 resolves the two north workcells with
`reviewed_yaw_deg: -90` under that convention, and adds source-composed
`evidence_camera` records. Scenario Forge preserves those records as producer
provenance, but does not map their source-room position directly to eBench: the
fixed recovered Lift2 may occlude a source-valid view. For a profiled zone,
`scene_overview` instead reuses the post-reset `workspace_closeup` camera
direction at a modestly larger distance, with the room visible. This affects
only evidence cameras; it never changes the task workcell or source USD.

## 3. Generate selectable task packages

After ConvertAsset returns the package and zone manifest, compile all eligible
zones. This selection occurs before an eBench episode; GenManip does not need a
runtime zone-switch feature.

```bash
PYTHONPATH=src python scripts/generate_scientific_workbench_background_variants.py \
  --base-package "$PWD/outputs/scientific_workbench_bimanual_pour" \
  --admission "$PWD/outputs/external_environment_3fo4k5c9jd44/scenario_forge_consumer_admission.yaml" \
  --background-root "$PWD/outputs/external_environment_3fo4k5c9jd44" \
  --external-intake "$PWD/outputs/external_environment_3fo4k5c9jd44/intake.yaml" \
  --workspace-zone-profiles "$ZONE_MANIFEST" \
  --background-asset-id scientific_environment_3fo4k5c9jd44 \
  --out "$PWD/outputs/scientific_workbench_external_room_zone_variants" \
  --render \
  --isaac-python "$ISAAC_ENV/bin/python" \
  --genmanip-root "$GENMANIP_CANARY"
```

The result has one ordinary task package per eligible workcell:

```text
scientific_workbench_external_room_zone_variants/
  scientific_environment_3fo4k5c9jd44__north_bench_pair_east/
  scientific_environment_3fo4k5c9jd44__north_bench_pair_west/
  scientific_environment_3fo4k5c9jd44__south_table_b/
  background_variants_manifest.json
```

Use `variants[].variant_id` in `background_variants_manifest.json` to choose a
package before starting an episode. `scene.asset_id` remains
`scientific_environment_3fo4k5c9jd44` in every output; only the background
instance pose, reviewed inactive roots, reviewed yaw, and scenario ID differ.
Use `--variant-id <asset-id>__<zone-id>` to rebuild one selected zone.
The external intake's source-tree and archive digests are echoed into each
variant's restricted background provenance and asset attribution; no staging
path or signed URL is copied into the package.

The delivered `east_bench` profile is deliberately `not_applicable`: it is
recorded as an exclusion in the aggregate manifest and must not be turned into
an envelope-centred fallback package. The v0.3 correction makes all three other
zones eligible: both north pairs use reviewed `-90` degree yaw and
`south_table_b` retains zero yaw.

## Visual review and acceptance

Start by retaining room clutter. Scenario Forge applies the required assembly
roots plus only the finite `optional_inactive_prim_paths` explicitly listed by
ConvertAsset for the selected zone. Those paths are producer-audited complete
actors that intersect the fixed eBench clearance; it does not infer extra
deletions, mask anonymous meshes, or mutate the source room.

For every candidate, retain and review:

- `adapters/ebench/genmanip/evidence/initial_scene/scene_overview.png`;
- `adapters/ebench/genmanip/evidence/initial_scene/workspace_closeup.png`; and
- the aggregate zone manifest/contact sheet.

Accept only zones where the room context, robot, table, flask, and graduated
cylinder are readable and no retained background workbench crosses the fixed
workspace. The runtime gate proves construction and required prim presence; a
separate image review decides presentation acceptance. For a camera-reference
overview, the structural gate additionally checks that the room is marked
visible and that its look-at/distance match the declared post-reset workspace
camera reference; it still does not judge image quality. Keep the best 3--5
visually distinct zones. If fewer pass, report the measured exclusions rather
than manufacturing placements.

Before zone profiling, accept the facade only when its evidence explicitly
shows that `/Root` room geometry is visible, `/world/Looks` bindings resolve,
the HDR/light data is package-local, and the package opens at `/World` from a
clean directory.

Finally run `package check --require-asset-lock` for every generated package
and open a copied package from a clean directory to confirm the ConvertAsset
closure has no source-tree USD, texture, or HDR dependency.

## Claim boundary

These packages prove visual-static room substitution with a fixed workcell.
They do not prove background interaction physics, oracle rollout, policy
success, or liquid-transfer success. Physical cropping into partial-room USD
packages is deliberately out of scope for this version.

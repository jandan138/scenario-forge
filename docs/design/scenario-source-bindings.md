# Scenario Source Bindings

`scenario-source-bindings/v0.3` is the current local build-input contract between a
portable `ScenarioSpec` and the USD closures used to compile it. It keeps machine
paths and ConvertAsset delivery locations out of `scenario.yaml` while preserving
the asset IDs used by the scenario. The resolver continues to accept v0.1 and v0.2
files; their ConvertAsset bindings retain the historical meanings and cannot opt
into the v0.3 static-support contract.

The dependency flow is:

```text
ScenarioSpec asset IDs + local source bindings
  -> LocalUSDAssetSource values
  -> portable scenario-package/v0.2
  -> optional GenManip collected-package export
```

The bindings file is an operational input, not package identity and not an asset
registry. It may contain absolute paths. Relative paths are resolved against the
directory containing the bindings file. Generated manifests and provenance retain
portable source URIs, upstream package identities, revisions, and content hashes;
they do not retain the local paths used for the build.

## Contract

The `bindings` keys are the asset IDs referenced by `scene.asset_id`,
`scene.overlay_asset_ids`, and object bindings in the ScenarioSpec. The first
version supports two resolvers.

`local_usd` maps one already usable USD closure directly into the neutral asset
source contract:

```yaml
schema_version: scenario-source-bindings/v0.2
bindings:
  scientific_workbench_environment:
    resolver: local_usd
    source_usd: ./lab_001/lab_001.usd
    role: environment
    license: CC-BY-NC-4.0
    source_uri: LabUtopia:lab_001_localized_20260707
    attribution:
      - "LabUtopia data assets: CC BY-NC 4.0"
    redistributable: false
    exclude_relative_paths: [_reports]
    root_prim_path: /World
    expected_sha256: sha256:...
```

`convert_asset_package` validates an existing source-bound ConvertAsset delivery
through the existing inbound adapter. Its `usage` explicitly selects the
neutral role instead of inferring one. The available values are `scene_overlay`,
`rigid_object`, `articulated_object`, `visual_static_environment`, and
`visual_static_object`. Version v0.3 additionally admits
`static_support_object` and v0.5 `dynamic_context_object`.

`dynamic_context_object` is for physically present scene dressing. It accepts
either a narrow passing `aan.dynamic_context_contract.v1` or the stronger
passing `aan.interaction_contract.v1`. Scenario objects using it must have
`role: context_prop`, fixed dressing preset/group metadata, and
`metric_participation: none`; adapters load its producer-owned physics but do
not add it to task metrics. The r10.1 VR adapter does add tabletop context props
to `obj_prim_list`, because the collection contract requires every tabletop
`obj_*` prim to participate in bounded local randomization.

The two `visual_static_*` values require a ConvertAsset `asset_role:
visual_static` manifest. Scenario Forge verifies the exact source and scope hashes,
the passing visual-preservation fingerprint and runtime render gate, the preserved
source/package physical frame and scoped world bounds, and zero active rigid body,
collision, joint, or articulation residue. They map respectively to
the neutral `environment` and `static_object` roles; neither may be used to smuggle
asset-specific physics into a package.

A `static_support_object` must instead come from a ConvertAsset `asset_role:
static_support` package. Scenario Forge verifies its source-bound identity, entry
scope, collision ownership, physical-material values, support surface, edge
geometry, and the six required runtime probes (centre drop, four edge drops, and a
side impact). The accepted v0.1 support policy uses the source collider when one is
already suitable, otherwise a package-owned proxy; it never delegates collider
creation to the consumer. The current table material defaults are static/dynamic
friction `0.5`, restitution `0.0`, friction combine `max`, and restitution combine
`multiply`.
These values are explicitly `provisional_unmeasured`; replacing them later means
publishing a new ConvertAsset profile/package, not patching a task consumer.

The EBench/GenManip adapter accepts a `static_object` or `static_support` only for
the scenario's declared table. For v0.3 static support, its episode layout points
at a thin runtime composition entry and explicitly sets `add_colliders: false` and
`add_rigid_body: false`; the producer package remains the only owner of support
physics. The historical v0.2 visual-static table path remains readable and retains
its old GenManip-generated support collider for compatibility, but new canonical
packages must not use it. A non-table static object is rejected before export.

```yaml
  scientific_workbench_scene1_hard_environment:
    resolver: convert_asset_package
    usage: visual_static_environment
    source_usd: ./Scene1_hard.usd
    package_dir: ./scene1_environment/package
    manifest_path: ./scene1_environment/manifest.json
    producer_revision: <ConvertAsset commit>
    expected_scope_prims: [/World/lab_015]
    license: CC-BY-NC-4.0
    attribution:
      - Scene1_hard parent-composed lab_015 visual room normalized by ConvertAsset
    redistributable: false
    exclude_relative_paths: [evidence]

  scientific_workbench_ebench_table:
    resolver: convert_asset_package
    usage: static_support_object
    source_usd: ./lab_001.usd
    package_dir: ./ebench_table/package
    manifest_path: ./ebench_table/manifest.json
    producer_revision: <ConvertAsset commit>
    expected_scope_prims: [/World/table]
    license: CC-BY-NC-4.0
    attribution:
      - EBench-compatible static support table qualified by ConvertAsset
    redistributable: false
```

`usage: rigid_object` is admitted only when the producer manifest contains a
task-ready `aan.interaction_contract.v1`. Scenario Forge verifies that the asset
entry prim is the single active rigid root, all declared colliders and authoritative
named frames are coherent, the contract/profile/runtime-tree hashes close, and the
required root-motion, stable-support, gripper-collision, and open-top gates passed.
Collider records may preserve or author an enabled collider, or explicitly disable
a source collider that has been replaced by package-owned geometry; the declared
`collision_enabled` value must agree with that mode.
Each passing gate must point to a package-relative runtime qualification report;
Scenario Forge verifies that file and its SHA-256. It then emits a
`LocalUSDAssetSource` with role `rigid_object`. Do not exclude `evidence/` from a
rigid-object binding: the compiler retains the qualification report in the asset
closure and locks it with the rest of the package. A static producer package with
`not_run` gates remains valid producer evidence, but is rejected for this task-ready
usage.

Both `rigid_object` and `articulated_object` are task-interactive references:
the scenario wrapper owns their final task pose. Their ConvertAsset entry prim
must therefore have an identity composed world transform within absolute
tolerance `1e-6`. Scenario Forge reads that matrix from
`visual_preservation_fingerprint.package_before_physics_profile.scope_world_transforms`
and rejects a producer package whose entry root still carries scale, rotation,
translation, pivot, or another effective canonicalization transform. It also
reads the matching `physics_closure.physical_frame.scope_bounds` entry and
transports it as `upstream_package.metadata.task_interactive_geometry`. This is
a generic composition contract, not an asset-specific repair. Historical
`scene_overlay` bindings and visual-static room/table packages retain their
existing transform behavior.

```yaml
  scientific_workbench_conical_bottle03_dynamic:
    resolver: convert_asset_package
    usage: rigid_object
    source_usd: ./lab_001/lab_001.usd
    package_dir: ./conical_bottle03/package
    manifest_path: ./conical_bottle03/manifest.json
    producer_revision: <ConvertAsset commit>
    expected_scope_prims: [/World/conical_bottle03]
    license: CC-BY-NC-4.0
    redistributable: false
```

`usage: articulated_object` is a separate dynamic handoff. It does not weaken or
reuse the single-rigid-root `interaction_contract`. Scenario Forge requires one
passing articulation root, a positive contiguous DOF map, finite non-degenerate
joint limits, and an in-range passing reset value for every mapped DOF. It also
requires a source-hash-bound `aan.articulated_device_profile.v1` and its passing,
hash-locked runtime qualification report. That report must include the actual
Isaac runtime DOF order (`runtime_dof_mapping` with index, runtime name, and joint
prim); Scenario Forge rejects a static closure whose indices differ from the
runtime vector. The profile also declares `required_runtime_task_gates`; the
report must contain a passing record for every declared gate, so a top-level
`status: pass` alone is insufficient. The profile supplies semantic joint names,
moving-part prims, named state intervals, reset states, and authoritative named
frames; all are checked against the manifest `articulation_closure`.

All profile frames may be retained as authoritative validation frames, including
frames parented below a moving articulated part. Current task materialization and
GenManip export can use only a frame whose `parent_prim` is the articulation root:
the exported portable pose has no moving-parent state/transform semantics. A
moving-parent frame therefore remains qualification evidence, not a
task/GenManip-exportable frame, until a future versioned contract defines its
state binding and transform evaluation. Do not flatten or infer it consumer-side.

The resulting upstream metadata exposes a simulator-neutral
`scenario-forge-articulation-contract/v0.1`:

```yaml
schema_version: scenario-forge-articulation-contract/v0.1
asset_entry_prim: /World/Centrifuge
articulation_root_prim: /World/Centrifuge
runtime_units:
  revolute: radian
  prismatic: meter
required_runtime_task_gates:
  - lid_contact_cycle
  - button_contact_cycle
joints:
  lid:
    joint_prim: /World/Centrifuge/lid_joint
    part_prim: /World/Centrifuge/lid
    runtime_reset_value: -1.553343
    states:
      open: [-1.570796, -1.396263]
      closed: [-0.087266, 0.0]
closure:
  articulation_roots: [...]
  dof_mapping: [...]
  reset_values: [...]
```

The complete verified AAN closure remains available separately as
`upstream_package.metadata.articulation_closure`. Bindings may not exclude the
device profile or runtime report, because those files are part of the accepted
contract rather than disposable preview evidence. AAN's raw USD revolute records
remain authored in degrees, while GenManip reads and writes articulation positions
in radians. The neutral contract therefore exposes explicit runtime units and
runtime reset/state values; the inbound adapter verifies the degree-to-radian
mapping instead of forwarding raw closure values into GenManip.

```yaml
  scientific_workbench_centrifuge:
    resolver: convert_asset_package
    usage: articulated_object
    source_usd: ./hci955350-normalized-facade/facade.usd
    package_dir: ./hci955350/package
    manifest_path: ./hci955350/manifest.json
    producer_revision: <ConvertAsset commit>
    expected_scope_prims: [/World/Centrifuge]
    license: LicenseRef-Internal-Restricted
    redistributable: false
```

The resolver calls `load_convert_asset_package_handoff`; it does not convert USD,
author physics, copy ConvertAsset implementation code, or weaken the producer's
source/hash/runtime gates. A replacement calibrated profile is selected by changing
the external binding to a new delivery, not by changing the ScenarioSpec.

GPU-PBD static containers use a separate narrow handoff because their producer
manifest binds a collision profile, a three-cold-run qualification report, and
an exact initial particle state. `load_gpu_pbd_static_container_handoff`
validates those package-local artifacts and their hashes, then exposes the USD
through the same neutral `LocalUSDAssetSource` boundary. Consumers must not add
asset-specific collision, scale, rest-offset, mass/inertia, or warning
suppression logic. The contract proves only the named static-containment claim;
it does not infer pouring or benchmark readiness.

Each cold run must also record `particle_readback_attribute: points`. Isaac Sim
4.1's `physxParticle:simulationPoints` is an authored rest-state buffer, not
live PBD evidence; reports based on it are rejected even if all artifact hashes
and older promotion fields are otherwise valid.

A qualified source/target transfer pair uses the adjacent
`load_gpu_pbd_transfer_pair_handoff` boundary. The loader verifies the promoted
component USD, package-local dependency tree, profile-bound particle count,
selected trajectory candidate, and three independent cold-run observations.
The v1 profile remains the original 548-particle, 40-FPS contract. A v2 profile
may bind a different positive particle count, settled-fill target, tolerance,
and declared minimum performance gate without changing the manifest identity
or weakening v1 consumers.
Each observation must use live `points` readback, retain all particles before
the pour, deliver at least half of them to the target, sustain at least 40 FPS,
and report no hard runtime error. Spill and below-support counts remain recorded
evidence rather than additional consumer policy gates.

This handoff proves prescribed-kinematic transfer feasibility only. Scenario
Forge may compose the producer component into an eBench scene, but it does not
turn the prescribed trajectory into a robot policy or activate a liquid metric.
Consumers must not patch either vessel's collider, scale, rest offset, or PBD
parameters. Robot transfer, metric correctness, and benchmark success remain
separate downstream claims.

Dynamic loaded starts add the narrower
`load_gpu_pbd_dynamic_loaded_start_handoff` boundary on top of a qualified
transfer pair. It verifies the package-local source-root particle state,
support-plane-to-entry-root pose, hashes, three cold starts, maximum outside
particle count, entry-root drift, tilt, and absence of hard runtime errors.
Scenario Forge may use the accepted pose to transform the vessel and its
source-local particles into one scene frame. It may not reinterpret that
evidence as a robot grasp, pour, policy, liquid metric, or benchmark claim.

## Compile command

```bash
scenario-forge package compile \
  --spec examples/scientific_workbench/bimanual_pour/scenario.yaml \
  --source-bindings /path/to/source_bindings.yaml \
  --out /tmp/scientific_workbench_bimanual_pour \
  --export-genmanip
```

`--export-genmanip` is explicit and optional. The command is a static compiler: it
does not start Isaac Sim, render previews, execute an oracle, or run an episode.
Those operations stay in the existing preview workflow and downstream EOS/GenManip.

The compiler derives `asset_lock.yaml` identity from `scenario_id`, so identical
specs, bindings, and unchanged source closures produce identical package contents
even when compiled under different output directory names. The standalone
`generate_asset_lock` API keeps its historical output-basename default unless a
caller supplies a stable `lock_id`.

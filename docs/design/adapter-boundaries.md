# Adapter Boundaries

Adapters translate portable packages into simulator or tool-specific artifacts.

Rules:

- Adapters consume portable packages; they do not mutate `manifest.yaml` in place.
- Adapters report blockers as structured issues.
- Heavy imports stay lazy or out-of-process.
- Optional simulator dependencies must not be required for `scenario-forge package check`.

## External Pipeline Integrations

LabBuilder-style and SimFoundry-style systems are external capability sources,
not Scenario Forge core dependencies.

Rules:

- LabBuilder-style integrations may produce protocol, required asset, layout,
  safety, and validation hints. They must enter Scenario Forge through
  `generation_plan.yaml`, `scene/layout.yaml`, `scene/instances.yaml`,
  `evidence/layout_checks.yaml`, `evidence/static_checks.yaml`, and provenance
  records.
- SimFoundry-style integrations may produce reconstructed assets, scene/object
  poses, physics metadata, task-cousin proposals, validation evidence, and source
  provenance. They must enter Scenario Forge through a real-to-sim importer under
  `src/scenario_forge/adapters/real2sim/`.
- External pipeline outputs must be normalized into Scenario Forge schemas before
  they appear in `manifest.yaml`; bespoke upstream pipeline schemas must not
  become package identity.
- External assets must go through `assets/asset_manifest.yaml` and
  `locks/asset_lock.yaml`. No adapter may bypass license, checksum, or provenance
  checks.
- Pipeline identity, versions, prompts, source media references, and model/tool
  versions belong in `locks/generator_lock.yaml`,
  `provenance/source_refs.yaml`, `provenance/generation_trace.jsonl`, or
  `evidence/*`, not in top-level package naming.
- Heavy reconstruction, simulator import, VLM/model calls, navigation evaluation,
  rollout collection, and benchmark reporting remain outside pure package layers.

Adoption gate:

1. Use a deterministic Scenario Forge baseline first.
2. Add an optional importer/adapter for an external pipeline only after its
   artifact contract, license terms, and dependency boundary are clear.
3. Compare external output against the baseline on package validity, asset-lock
   coverage, task predicate binding, reachability, collision/safety checks, and
   EBench adapter readiness.
4. Promote the external pipeline from reference to supported adapter only when it
   improves those checks without weakening portability.

## ConvertAsset

ConvertAsset remains the owner of USD/MDL/mesh conversion and asset-level physics
normalization. Scenario Forge supports both an outbound command-plan boundary and
an inbound package boundary; neither imports ConvertAsset implementation code.

Preferred high-level path:

```text
ConvertAsset/scripts/isaac_python.sh ConvertAsset/main.py normalize-asset <source.usd> --out <package-dir>
```

Low-level commands such as `no-mdl`, `mesh-faces`, and `usd-to-glb` remain ConvertAsset-owned.

For an inbound normalized USD package, the ConvertAsset adapter validates and maps
the producer's package/manifest contract into a Scenario Forge
`LocalUSDAssetSource` plus portable `UpstreamPackageRef` provenance. In particular,
it checks that the package is bound to the exact source USD hash, that the external
and embedded manifests agree, that entry points and scoped prims are safe and
expected, and that the declared profile and runtime gates passed. It does not
author mass, inertia, center of mass, collision, or rigid-body opinions; delete
physics APIs; suppress warnings; or otherwise repair the USD locally.

The consuming package retains the runtime closure needed by the normalized root
USD, including `deps/`, `physics/`, and `overlays/`. Producer-side `evidence/` is
excluded from the copied runtime closure. Its manifest is consumed at compile time
and represented by a portable URI, content hash, producer revision, and bounded
handoff metadata in Scenario Forge manifests/provenance rather than by vendoring
the upstream evidence tree.

Scene packages can compose such a source-bound package with a base environment
through `scene.overlay_asset_ids` in `scenario-spec/v0.2` and later. Overlay ordering and
strength are defined in
[Scene Asset Overlays](scene-asset-overlays.md). A later calibrated profile is an
upstream package replacement: Scenario Forge consumes the replacement
package/manifest and updates provenance, without gaining a second physics-repair
implementation.

## Isaac

The planned Isaac adapter will write:

```text
adapters/isaac/scene.usd
adapters/isaac/run_config.yaml
```

It must keep `pxr` and `omni.*` imports out of pure package layers.
